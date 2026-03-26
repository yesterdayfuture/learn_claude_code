#!/usr/bin/env python3
# Harness: team mailboxes -- multiple models, coordinated through files.
"""
s09_agent_teams.py - Agent Teams

Persistent named agents with file-based JSONL inboxes. Each teammate runs
its own agent loop in a separate thread. Communication via append-only inboxes.

    Subagent (s04):  spawn -> execute -> return summary -> destroyed
    Teammate (s09):  spawn -> work -> idle -> work -> ... -> shutdown

    .team/config.json                   .team/inbox/
    +----------------------------+      +------------------+
    | {"team_name": "default",   |      | alice.jsonl      |
    |  "members": [              |      | bob.jsonl        |
    |    {"name":"alice",        |      | lead.jsonl       |
    |     "role":"coder",        |      +------------------+
    |     "status":"idle"}       |
    |  ]}                        |      send_message("alice", "fix bug"):
    +----------------------------+        open("alice.jsonl", "a").write(msg)

                                        read_inbox("alice"):
    spawn_teammate("alice","coder",...)   msgs = [json.loads(l) for l in ...]
         |                                open("alice.jsonl", "w").close()
         v                                return msgs  # drain
    Thread: alice             Thread: bob
    +------------------+      +------------------+
    | agent_loop       |      | agent_loop       |
    | status: working  |      | status: idle     |
    | ... runs tools   |      | ... waits ...    |
    | status -> idle   |      |                  |
    +------------------+      +------------------+

    5 message types (all declared, not all handled here):
    +-------------------------+-----------------------------------+
    | message                 | Normal text message               |
    | broadcast               | Sent to all teammates             |
    | shutdown_request        | Request graceful shutdown (s10)   |
    | shutdown_response       | Approve/reject shutdown (s10)     |
    | plan_approval_response  | Approve/reject plan (s10)         |
    +-------------------------+-----------------------------------+

Key insight: "Teammates that can talk to each other."
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

SYSTEM = f"You are a team lead at {WORKDIR}. Manage teammates with shutdown and plan approval protocols."

VALID_MSG_TYPES = {
    "message",
    "broadcast",
    "shutdown_request",
    "shutdown_response",
    "plan_approval_response",
}

# -- Request trackers: correlate by request_id --
shutdown_requests = {}
plan_requests = {}
_tracker_lock = threading.Lock()


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
        sys_prompt = (
            f"You are '{name}', role: {role}, at {WORKDIR}. "
            f"Use send_message to communicate. Complete your task."
        )
        messages = [{"role": "user", "content": prompt}]

        # 获取可用的工具
        tools = self._teammate_tools()
        should_exit = False

        for _ in range(50):

            # 获取其他角色发送的消息
            inbox = BUS.read_inbox(name)

            # 将inbox中的消息添加到messages中
            for msg in inbox:
                messages.append({"role": "user", "content": json.dumps(msg)})
            # 如果上级发送了shutdown_request，则退出
            if should_exit:
                break
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto"
                )

            except Exception:
                break
                # Append assistant turn
            messages.append({"role": "assistant",
                             "content": response.choices[-1].message.content})
            # If the model didn't call a tool, we're done

            tool_calls = response.choices[-1].message.tool_calls
            if not tool_calls or len(tool_calls) == 0:
                break

            messages.append({"role": "assistant", "content": None, "tool_calls": tool_calls})
            results = []
            for block in tool_calls:
                params = json.loads(block.function.arguments)
                function_name = block.function.name

                output = self._exec(name, function_name, params)
                print(f"  [{name}] {function_name}: {str(output)[:120]}")

                results.append({"role": "tool", "tool_call_id": block.id,
                                "content": output})

                if function_name == "shutdown_response" and params.get("approve"):
                    should_exit = True

            messages.extend(results)

        # 当前成员结束任务，在团队中改变状态为idle
        member = self._find_member(name)
        if member:
            member["status"] = "shutdown" if should_exit else "idle"
            self._save_config()

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
            query = input("\033[36ms10 >> \033[0m")
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
