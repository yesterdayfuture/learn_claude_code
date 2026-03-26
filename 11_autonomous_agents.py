#!/usr/bin/env python3
# Harness: autonomy -- models that find work without being told.
"""
s11_autonomous_agents.py - Autonomous Agents

Idle cycle with task board polling, auto-claiming unclaimed tasks, and
identity re-injection after context compression. Builds on s10's protocols.

    Teammate lifecycle:
    +-------+
    | spawn |
    +---+---+
        |
        v
    +-------+  tool_use    +-------+
    | WORK  | <----------- |  LLM  |
    +---+---+              +-------+
        |
        | stop_reason != tool_use
        v
    +--------+
    | IDLE   | poll every 5s for up to 60s
    +---+----+
        |
        +---> check inbox -> message? -> resume WORK
        |
        +---> scan .tasks/ -> unclaimed? -> claim -> resume WORK
        |
        +---> timeout (60s) -> shutdown

    Identity re-injection after compression:
    messages = [identity_block, ...remaining...]
    "You are 'coder', role: backend, team: my-team"

Key insight: "The agent finds work itself."
"""

import os
import subprocess
from pathlib import Path
import json
import threading
import time
import uuid
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

WORKDIR = Path.cwd()
client = OpenAI(
    api_key=os.getenv("api_key"),
    base_url=os.getenv("base_url"),
)
MODEL = os.getenv("model")

TEAM_DIR = WORKDIR / ".team"
INBOX_DIR = TEAM_DIR / "inbox"
TASKS_DIR = WORKDIR / ".tasks"

# 空闲状态下，每次循环等待时间
POLL_INTERVAL = 5
# 空闲状态下，最长等待时间
IDLE_TIMEOUT = 60

SYSTEM = f"You are a team lead at {WORKDIR}. Teammates are autonomous -- they find work themselves."

VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_response",
}

# -- Request trackers --
shutdown_requests = {}
plan_requests = {}
_tracker_lock = threading.Lock()
_claim_lock = threading.Lock()


# -- Task board scanning 任务扫描--
def scan_unclaimed_tasks() -> list:
    TASKS_DIR.mkdir(exist_ok=True)
    unclaimed = []
    for f in sorted(TASKS_DIR.glob("task_*.json")):
        task = json.loads(f.read_text())
        if (task.get("status") == "pending"
                and not task.get("owner")
                and not task.get("blockedBy")):
            unclaimed.append(task)
    return unclaimed


# 任务领取
def claim_task(task_id: int, owner: str) -> str:
    with _claim_lock:
        path = TASKS_DIR / f"task_{task_id}.json"
        if not path.exists():
            return f"Error: Task {task_id} not found"
        task = json.loads(path.read_text())
        task["owner"] = owner
        task["status"] = "in_progress"
        path.write_text(json.dumps(task, indent=2))
    return f"Claimed task #{task_id} for {owner}"


# -- Identity re-injection after compression , 身份信息重新注入--
def make_identity_block(name: str, role: str, team_name: str) -> dict:
    return {
        "role": "user",
        "content": f"<identity>You are '{name}', role: {role}, team: {team_name}. Continue your work.</identity>",
    }


# -- MessageBus: JSONL inbox per teammate --
class MessageBus:
    def __init__(self, inbox_dir: Path):
        self.dir = inbox_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def send(self, sender: str, to: str, content: str,
             msg_type: str = "message", extra: dict = None) -> str:
        if msg_type not in VALID_MSG_TYPES:
            return f"Error: Invalid type '{msg_type}'. Valid: {VALID_MSG_TYPES}"
        msg = {
            "type": msg_type,
            "from": sender,
            "content": content,
            "timestamp": time.time(),
        }
        if extra:
            msg.update(extra)
        inbox_path = self.dir / f"{to}.jsonl"
        with open(inbox_path, "a") as f:
            f.write(json.dumps(msg) + "\n")
        return f"Sent {msg_type} to {to}"

    def read_inbox(self, name: str) -> list:
        inbox_path = self.dir / f"{name}.jsonl"
        if not inbox_path.exists():
            return []
        messages = []
        for line in inbox_path.read_text().strip().splitlines():
            if line:
                messages.append(json.loads(line))
        inbox_path.write_text("")
        return messages

    def broadcast(self, sender: str, content: str, teammates: list) -> str:
        count = 0
        for name in teammates:
            if name != sender:
                self.send(sender, name, content, "broadcast")
                count += 1
        return f"Broadcast to {count} teammates"


BUS = MessageBus(INBOX_DIR)

# -- TeammateManager: persistent named agents with config.json --
"""
角色的信息数据格式：
{
"name":名称,
"status":idle、working、shutdown,
"role":角色,
}
"""


class TeammateManager:
    def __init__(self, team_dir: Path):
        self.dir = team_dir
        self.dir.mkdir(exist_ok=True)
        self.config_path = self.dir / "config.json"
        self.config = self._load_config()
        self.threads = {}

    def _load_config(self) -> dict:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text())
        return {"team_name": "default", "members": []}

    def _save_config(self):
        self.config_path.write_text(json.dumps(self.config, indent=2))

    def _find_member(self, name: str) -> dict:
        for m in self.config["members"]:
            if m["name"] == name:
                return m
        return None

    def _set_status(self, name: str, status: str):
        member = self._find_member(name)
        if member:
            member["status"] = status
            self._save_config()

    def spawn(self, name: str, role: str, prompt: str) -> str:
        member = self._find_member(name)
        if member:
            if member["status"] not in ("idle", "shutdown"):
                return f"Error: '{name}' is currently {member['status']}"
            member["status"] = "working"
            member["role"] = role
        else:
            member = {"name": name, "role": role, "status": "working"}
            self.config["members"].append(member)
        self._save_config()
        thread = threading.Thread(
            target=self._teammate_loop,
            args=(name, role, prompt),
            daemon=True,
        )
        self.threads[name] = thread
        thread.start()
        return f"Spawned '{name}' (role: {role})"

    def _teammate_loop(self, name: str, role: str, prompt: str):
        team_name = self.config["team_name"]
        sys_prompt = (
            f"You are '{name}', role: {role}, team: {team_name}, at {WORKDIR}. "
            f"Use idle tool when you have no more work. You will auto-claim new tasks."
        )
        messages = [{"role": "assistant", "content": sys_prompt}, {"role": "user", "content": prompt}]

        # 获取可用的工具
        tools = self._teammate_tools()

        while True:

            for _ in range(50):

                # 获取其他角色发送的消息
                inbox = BUS.read_inbox(name)

                # 将inbox中的消息添加到messages中
                for msg in inbox:
                    # 如果上级发送了shutdown_request，则退出
                    if msg.get("type") == "shutdown_request":
                        self._set_status(name, "shutdown")
                        return
                    messages.append({"role": "user", "content": json.dumps(msg)})

                try:
                    response = client.chat.completions.create(
                        model=MODEL,
                        messages=messages,
                        tools=tools,
                        tool_choice="auto"
                    )

                except Exception:
                    self._set_status(name, "idle")
                    return
                    # Append assistant turn
                messages.append({"role": "assistant",
                                 "content": response.choices[-1].message.content})
                # If the model didn't call a tool, we're done

                tool_calls = response.choices[-1].message.tool_calls
                if not tool_calls or len(tool_calls) == 0:
                    break

                messages.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
                results = []
                # 是否空闲标志
                idle_requested = False

                for block in tool_calls:
                    params = json.loads(block.function.arguments)
                    function_name = block.function.name

                    if function_name == "idle":
                        idle_requested = True
                        output = "Entering idle phase. Will poll for new tasks."
                    else:
                        output = self._exec(name, function_name, params)
                    print(f"  [{name}] {function_name}: {str(output)[:120]}")

                    results.append({"role": "tool", "tool_call_id": block.id,
                                    "content": output})

                messages.extend(results)
                # 如果空闲，就结束工作状态
                if idle_requested:
                    break

            # -- 空闲状态，扫描任务面板，按要求领取任务 --
            self._set_status(name, "idle")

            # 是否关闭当前智能体
            resume = False
            polls = IDLE_TIMEOUT // max(POLL_INTERVAL, 1)
            for _ in range(polls):
                time.sleep(POLL_INTERVAL)

                # 获取其他角色发送的消息
                inbox = BUS.read_inbox(name)
                if inbox:
                    for msg in inbox:
                        if msg.get("type") == "shutdown_request":
                            self._set_status(name, "shutdown")
                            return
                        messages.append({"role": "user", "content": json.dumps(msg)})
                    resume = True
                    break

                # 扫描任务面板，获取未领取的任务
                unclaimed = scan_unclaimed_tasks()
                if unclaimed:
                    task = unclaimed[0]
                    claim_task(task["id"], name)
                    task_prompt = (
                        f"<auto-claimed>Task #{task['id']}: {task['subject']}\n"
                        f"{task.get('description', '')}</auto-claimed>"
                    )
                    if len(messages) <= 3:
                        messages.insert(0, make_identity_block(name, role, team_name))
                        messages.insert(1, {"role": "assistant", "content": f"I am {name}. Continuing."})
                    messages.append({"role": "user", "content": task_prompt})
                    messages.append(
                        {"role": "assistant", "content": f"Claimed task #{task['id']}. Working on it."})
                    resume = True
                    break

            # 当前智能体为空闲状态，且在指定时间内未获取到任务，则关闭该智能体
            if not resume:
                self._set_status(name, "shutdown")
                return
            self._set_status(name, "working")

    def _exec(self, sender: str, tool_name: str, args: dict) -> str:
        # these base tools are unchanged from s02
        if tool_name == "bash":
            return run_bash(args["command"])
        if tool_name == "read_file":
            return run_read(args["path"])
        if tool_name == "write_file":
            return run_write(args["path"], args["content"])
        if tool_name == "edit_file":
            return run_edit(args["path"], args["old_text"], args["new_text"])
        if tool_name == "send_message":
            return BUS.send(sender, args["to"], args["content"], args.get("msg_type", "message"))
        if tool_name == "read_inbox":
            return json.dumps(BUS.read_inbox(sender), indent=2)
        if tool_name == "shutdown_response":
            req_id = args["request_id"]
            approve = args["approve"]
            with _tracker_lock:
                if req_id in shutdown_requests:
                    shutdown_requests[req_id]["status"] = "approved" if approve else "rejected"
            BUS.send(
                sender, "lead", args.get("reason", ""),
                "shutdown_response", {"request_id": req_id, "approve": approve},
            )
            return f"Shutdown {'approved' if approve else 'rejected'}"
        if tool_name == "plan_approval":
            plan_text = args.get("plan", "")
            req_id = str(uuid.uuid4())[:8]
            with _tracker_lock:
                plan_requests[req_id] = {"from": sender, "plan": plan_text, "status": "pending"}
            BUS.send(
                sender, "lead", plan_text, "plan_approval_response",
                {"request_id": req_id, "plan": plan_text},
            )
            return f"Plan submitted (request_id={req_id}). Waiting for lead approval."
        if tool_name == "claim_task":
            return claim_task(args["task_id"], sender)
        return f"Unknown tool: {tool_name}"

    def _teammate_tools(self) -> list:
        # these base tools are unchanged from s02
        return [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "description": "Run a shell command.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string"
                            }
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read file contents.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string"
                            },
                            "limit": {
                                "type": "integer"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {"name": "write_file", "description": "Write content to file.",
                             "parameters": {"type": "object",
                                            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                                            "required": ["path", "content"]}}
            },
            {
                "type": "function",
                "function": {"name": "edit_file", "description": "Replace exact text in file.",
                             "parameters": {"type": "object",
                                            "properties": {"path": {"type": "string"}, "old_text": {"type": "string"},
                                                           "new_text": {"type": "string"}},
                                            "required": ["path", "old_text", "new_text"]}}},
            {
                "type": "function",
                "function": {"name": "send_message", "description": "Send message to a teammate.",
                             "parameters": {"type": "object",
                                            "properties": {"to": {"type": "string"}, "content": {"type": "string"},
                                                           "msg_type": {"type": "string",
                                                                        "enum": list(VALID_MSG_TYPES)}},
                                            "required": ["to", "content"]}},
            },
            {
                "type": "function",
                "function": {"name": "read_inbox", "description": "Read and drain your inbox.",
                             "parameters": {"type": "object", "properties": {}}},
            },
            {
                "type": "function",
                "function": {"name": "shutdown_response",
                             "description": "Respond to a shutdown request. Approve to shut down, reject to keep working.",
                             "parameters": {"type": "object", "properties": {"request_id": {"type": "string"},
                                                                             "approve": {"type": "boolean"},
                                                                             "reason": {"type": "string"}},
                                            "required": ["request_id", "approve"]}},

            },
            {
                "type": "function",
                "function": {"name": "plan_approval",
                             "description": "Submit a plan for lead approval. Provide plan text.",
                             "parameters": {"type": "object", "properties": {"plan": {"type": "string"}},
                                            "required": ["plan"]}},
            },
            {
                "type": "function",
                "function": {"name": "idle",
                             "description": "Signal that you have no more work. Enters idle polling phase.",
                             "parameters": {"type": "object", "properties": {}}},

            },
            {
                "type": "function",
                "function": {"name": "claim_task", "description": "Claim a task from the task board by ID.",
                             "parameters": {"type": "object", "properties": {"task_id": {"type": "integer"}},
                                            "required": ["task_id"]}},
            }
        ]

    def list_all(self) -> str:
        if not self.config["members"]:
            return "No teammates."
        lines = [f"Team: {self.config['team_name']}"]
        for m in self.config["members"]:
            lines.append(f"  {m['name']} ({m['role']}): {m['status']}")
        return "\n".join(lines)

    def member_names(self) -> list:
        return [m["name"] for m in self.config["members"]]


TEAM = TeammateManager(TEAM_DIR)


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def run_read(path: str, limit: int = None) -> str:
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: Text not found in {path}"
        fp.write_text(content.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


# -- Lead-specific protocol handlers --
def handle_shutdown_request(teammate: str) -> str:
    req_id = str(uuid.uuid4())[:8]
    with _tracker_lock:
        shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
    BUS.send(
        "lead", teammate, "Please shut down gracefully.",
        "shutdown_request", {"request_id": req_id},
    )
    return f"Shutdown request {req_id} sent to '{teammate}' (status: pending)"


def handle_plan_review(request_id: str, approve: bool, feedback: str = "") -> str:
    with _tracker_lock:
        req = plan_requests.get(request_id)
    if not req:
        return f"Error: Unknown plan request_id '{request_id}'"
    with _tracker_lock:
        req["status"] = "approved" if approve else "rejected"
    BUS.send(
        "lead", req["from"], feedback, "plan_approval_response",
        {"request_id": request_id, "approve": approve, "feedback": feedback},
    )
    return f"Plan {req['status']} for '{req['from']}'"


def _check_shutdown_status(request_id: str) -> str:
    with _tracker_lock:
        return json.dumps(shutdown_requests.get(request_id, {"error": "not found"}))


# -- The dispatch map: {tool_name: handler} --
TOOL_HANDLERS = {
    "bash": lambda **kw: run_bash(kw["command"]),
    "read_file": lambda **kw: run_read(kw["path"], kw.get("limit")),
    "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
    "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
    "spawn_teammate": lambda **kw: TEAM.spawn(kw["name"], kw["role"], kw["prompt"]),
    "list_teammates": lambda **kw: TEAM.list_all(),
    "send_message": lambda **kw: BUS.send("lead", kw["to"], kw["content"], kw.get("msg_type", "message")),
    "read_inbox": lambda **kw: json.dumps(BUS.read_inbox("lead"), indent=2),
    "broadcast": lambda **kw: BUS.broadcast("lead", kw["content"], TEAM.member_names()),
    "shutdown_request": lambda **kw: handle_shutdown_request(kw["teammate"]),
    "shutdown_response": lambda **kw: _check_shutdown_status(kw.get("request_id", "")),
    "plan_approval": lambda **kw: handle_plan_review(kw["request_id"], kw["approve"], kw.get("feedback", "")),
    "idle": lambda **kw: "Lead does not idle.",
    "claim_task": lambda **kw: claim_task(kw["task_id"], "lead"),
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string"
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string"
                    },
                    "limit": {
                        "type": "integer"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {"name": "write_file", "description": "Write content to file.",
                     "parameters": {"type": "object",
                                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                                    "required": ["path", "content"]}}
    },
    {
        "type": "function",
        "function": {"name": "edit_file", "description": "Replace exact text in file.",
                     "parameters": {"type": "object",
                                    "properties": {"path": {"type": "string"}, "old_text": {"type": "string"},
                                                   "new_text": {"type": "string"}},
                                    "required": ["path", "old_text", "new_text"]}}},
    {
        "type": "function",
        "function": {"name": "spawn_teammate",
                     "description": "Spawn a persistent teammate that runs in its own thread.",
                     "parameters": {"type": "object",
                                    "properties": {"name": {"type": "string"}, "role": {"type": "string"},
                                                   "prompt": {"type": "string"}},
                                    "required": ["name", "role", "prompt"]}},
    },
    {
        "type": "function",
        "function": {"name": "list_teammates", "description": "List all teammates with name, role, status.",
                     "parameters": {"type": "object", "properties": {}}},
    },
    {
        "type": "function",
        "function": {"name": "send_message", "description": "Send message to a teammate.",
                     "parameters": {"type": "object",
                                    "properties": {"to": {"type": "string"}, "content": {"type": "string"},
                                                   "msg_type": {"type": "string",
                                                                "enum": list(VALID_MSG_TYPES)}},
                                    "required": ["to", "content"]}},
    },
    {
        "type": "function",
        "function": {"name": "read_inbox", "description": "Read and drain your inbox.",
                     "parameters": {"type": "object", "properties": {}}},
    },
    {
        "type": "function",
        "function": {"name": "broadcast", "description": "Send a message to all teammates.",
                     "parameters": {"type": "object", "properties": {"content": {"type": "string"}},
                                    "required": ["content"]}},
    },
    {
        "type": "function",
        "function": {"name": "shutdown_request",
                     "description": "Request a teammate to shut down gracefully. Returns a request_id for tracking.",
                     "parameters": {"type": "object", "properties": {"teammate": {"type": "string"}},
                                    "required": ["teammate"]}},

    },
    {
        "type": "function",
        "function": {"name": "shutdown_response",
                     "description": "Check the status of a shutdown request by request_id.",
                     "parameters": {"type": "object", "properties": {"request_id": {"type": "string"}},
                                    "required": ["request_id"]}},
    },
    {
        "type": "function",
        "function": {"name": "plan_approval",
                     "description": "Approve or reject a teammate's plan. Provide request_id + approve + optional feedback.",
                     "parameters": {"type": "object",
                                    "properties": {"request_id": {"type": "string"}, "approve": {"type": "boolean"},
                                                   "feedback": {"type": "string"}},
                                    "required": ["request_id", "approve"]}},

    },
    {
        "type": "function",
        "function": {"name": "idle", "description": "Enter idle state (for lead -- rarely used).",
                     "parameters": {"type": "object", "properties": {}}},
    },
    {
        "type": "function",
        "function": {"name": "claim_task", "description": "Claim a task from the board by ID.",
                     "parameters": {"type": "object", "properties": {"task_id": {"type": "integer"}},
                                    "required": ["task_id"]}},
    }
]


def agent_loop(messages: list):
    while True:
        inbox = BUS.read_inbox("lead")
        if inbox:
            messages.append({
                "role": "user",
                "content": f"<inbox>{json.dumps(inbox, indent=2)}</inbox>",
            })
            messages.append({
                "role": "assistant",
                "content": "Noted inbox messages.",
            })
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )
        # Append assistant turn
        messages.append({"role": "assistant",
                         "content": response.choices[-1].message.content})
        # If the model didn't call a tool, we're done

        tool_calls = response.choices[-1].message.tool_calls
        if not tool_calls or len(tool_calls) == 0:
            return

        messages.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
        results = []
        for block in tool_calls:
            params = json.loads(block.function.arguments)
            function_name = block.function.name

            handler = TOOL_HANDLERS.get(function_name)
            output = handler(**params) if handler else f"Unknown tool: {function_name}"
            print(f"> {function_name}: {output[:200]}")

            results.append({"role": "tool", "tool_call_id": block.id,
                            "content": output})

        messages.extend(results)


if __name__ == "__main__":
    history = [{"role": "system", "content": SYSTEM}]
    while True:
        try:
            query = input("\033[36ms11 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        if query.strip() == "/team":
            print(TEAM.list_all())
            continue
        if query.strip() == "/inbox":
            print(json.dumps(BUS.read_inbox("lead"), indent=2))
            continue

        if query.strip() == "/tasks":
            TASKS_DIR.mkdir(exist_ok=True)
            for f in sorted(TASKS_DIR.glob("task_*.json")):
                t = json.loads(f.read_text())
                marker = {"pending": "[ ]", "in_progress": "[>]", "completed": "[x]"}.get(t["status"], "[?]")
                owner = f" @{t['owner']}" if t.get("owner") else ""
                print(f"  {marker} #{t['id']}: {t['subject']}{owner}")
            continue

        if query.strip() == "/shut_down_record":
            print(json.dumps(shutdown_requests, indent=2))
            continue

        if query.strip() == "/plan_record":
            print(json.dumps(plan_requests, indent=2))
            continue

        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        print("\033[32m" + response_content + "\033[0m")
        print()
