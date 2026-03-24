"""
WebSocket 连接管理中心 - FastAPI 后端服务
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


# 存储所有活动的 WebSocket 连接
# 格式：{client_id: websocket}
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_logs: List[dict] = []
        self.max_logs = 100
    
    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self._add_log("connect", client_id, "Connection established")
    
    def disconnect(self, client_id: str) -> None:
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            self._add_log("disconnect", client_id, "Connection closed")
    
    async def send_personal_message(self, message: dict, client_id: str) -> None:
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                print(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict, exclude_client_id: Optional[str] = None) -> None:
        for client_id, connection in list(self.active_connections.items()):
            if client_id != exclude_client_id:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error broadcasting to {client_id}: {e}")
                    self.disconnect(client_id)
    
    def get_connection_count(self) -> int:
        return len(self.active_connections)
    
    def get_all_connections(self) -> List[dict]:
        return [
            {
                "client_id": client_id,
                "status": "active",
                "connected_at": datetime.now().isoformat()
            }
            for client_id in self.active_connections.keys()
        ]
    
    def _add_log(self, event_type: str, client_id: str, message: str) -> None:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "client_id": client_id,
            "message": message
        }
        self.connection_logs.append(log_entry)
        # 保持日志数量在限制内
        if len(self.connection_logs) > self.max_logs:
            self.connection_logs = self.connection_logs[-self.max_logs:]
    
    def get_recent_logs(self, limit: int = 50) -> List[dict]:
        return self.connection_logs[-limit:]


# 创建全局管理器实例
manager = ConnectionManager()


# Pydantic 模型
class Message(BaseModel):
    content: str
    client_id: Optional[str] = None


class BroadcastMessage(BaseModel):
    message: str
    type: str = "broadcast"


class StatsResponse(BaseModel):
    active_connections: int
    total_clients_today: int
    status: str


# Lifespan 上下文管理
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时的初始化
    print("🚀 WebSocket Connection Manager Starting...")
    yield
    # 关闭时的清理
    print("🛑 WebSocket Connection Manager Shutting down...")
    # 关闭所有连接
    for client_id, websocket in list(manager.active_connections.items()):
        await websocket.close(code=1001, reason="Server shutting down")


# 创建 FastAPI 应用
app = FastAPI(
    title="WebSocket Connection Manager",
    description="A centralized WebSocket connection management system",
    version="1.0.0",
    lifespan=lifespan
)


# RESTful API 端点

@app.get("/", response_class=HTMLResponse)
async def root():
    """返回前端首页"""
    try:
        with open("../frontend/dist/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(
            content="""
            <html>
            <head><title>WebSocket Manager</title></head>
            <body>
                <h1>WebSocket Connection Manager</h1>
                <p>请构建并部署前端应用到 /dist 目录，或单独访问前端地址。</p>
                <a href="/docs">API Documentation</a> | 
                <a href="/websocket-test">WebSocket Test Page</a>
            </body>
            </html>
            """,
            status_code=200
        )


@app.get("/api/connections", summary="获取所有活跃连接")
async def get_connections():
    """获取当前所有活跃的 WebSocket 连接"""
    connections = manager.get_all_connections()
    return {
        "success": True,
        "data": connections,
        "count": len(connections),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/message/broadcast", summary="广播消息")
async def broadcast_message(broadcast_msg: BroadcastMessage):
    """向所有连接广播消息"""
    message = {
        "type": broadcast_msg.type,
        "content": broadcast_msg.message,
        "timestamp": datetime.now().isoformat(),
        "sender": "server"
    }
    await manager.broadcast(message)
    return {
        "success": True,
        "message": "Message broadcasted successfully",
        "recipient_count": manager.get_connection_count()
    }


@app.get("/api/stats", summary="获取统计信息")
async def get_stats():
    """获取连接统计信息"""
    stats = StatsResponse(
        active_connections=manager.get_connection_count(),
        total_clients_today=len(manager.connection_logs),  # 简化处理
        status="running"
    )
    return {"success": True, "data": stats.dict()}


@app.get("/api/logs", summary="获取连接日志")
async def get_logs(limit: int = 50):
    """获取最近的连接日志"""
    logs = manager.get_recent_logs(limit)
    return {
        "success": True,
        "data": logs,
        "count": len(logs)
    }


# WebSocket 端点

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket 连接端点
    - 接受客户端连接
    - 处理双向消息通信
    - 自动断开非活动连接
    """
    await manager.connect(client_id, websocket)
    print(f"✅ Client {client_id} connected. Total: {manager.get_connection_count()}")
    
    # 发送欢迎消息
    welcome_msg = {
        "type": "welcome",
        "content": f"Welcome to WebSocket Connection Manager!",
        "client_id": client_id,
        "timestamp": datetime.now().isoformat()
    }
    await websocket.send_json(welcome_msg)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            print(f"📨 Received from {client_id}: {data}")
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                message = {"content": data}
            
            # 响应消息
            response = {
                "type": "response",
                "content": f"Echo: {message.get('content', data)}",
                "client_id": client_id,
                "timestamp": datetime.now().isoformat(),
                "received_at": datetime.now().isoformat()
            }
            
            await websocket.send_json(response)
            manager._add_log("message", client_id, f"Received: {data[:50]}")
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"❌ Client {client_id} disconnected. Total: {manager.get_connection_count()}")
    except Exception as e:
        print(f"❌ Error with client {client_id}: {e}")
        manager.disconnect(client_id)


# WebSocket 测试页面（简单 HTML）
@app.get("/websocket-test")
async def websocket_test():
    """提供一个简单的 WebSocket 测试页面"""
    return HTMLResponse(content="""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebSocket 测试</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; background: white; border-radius: 16px; padding: 30px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
        h1 { color: #333; text-align: center; margin-bottom: 30px; }
        .status-bar { display: flex; justify-content: space-between; align-items: center; padding: 15px; background: #f8f9fa; border-radius: 8px; margin-bottom: 20px; }
        .status { padding: 8px 16px; border-radius: 20px; font-weight: bold; }
        .status.connected { background: #d4edda; color: #155724; }
        .status.disconnected { background: #f8d7da; color: #721c24; }
        .controls { display: flex; gap: 10px; margin-bottom: 20px; }
        button { padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600; transition: all 0.3s; }
        button.connect { background: #28a745; color: white; }
        button.connect:hover { background: #218838; }
        button.disconnect { background: #dc3545; color: white; }
        button.disconnect:hover { background: #c82333; }
        button:disabled { opacity: 0.5; cursor: not-allowed; }
        .message-area { height: 300px; overflow-y: auto; border: 2px solid #e9ecef; border-radius: 8px; padding: 15px; margin-bottom: 20px; background: #fafafa; }
        .message { padding: 10px; margin: 8px 0; border-radius: 8px; animation: fadeIn 0.3s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        .message.received { background: #e7f3ff; border-left: 4px solid #007bff; }
        .message.sent { background: #d4edda; border-left: 4px solid #28a745; margin-left: auto; max-width: 70%; }
        .input-area { display: flex; gap: 10px; }
        input[type="text"] { flex: 1; padding: 12px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px; }
        input[type="text"]:focus { outline: none; border-color: #007bff; }
        button.send { background: #007bff; color: white; }
        button.send:hover { background: #0056b3; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-top: 20px; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
        .stat-card h3 { font-size: 24px; color: #667eea; margin-bottom: 5px; }
        .stat-card p { color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 WebSocket 连接测试</h1>
        
        <div class="status-bar">
            <span id="clientId">Client ID: </span>
            <div id="connectionStatus" class="status disconnected">未连接</div>
        </div>
        
        <div class="controls">
            <button id="connectBtn" class="connect" onclick="connect()">连接到服务器</button>
            <button id="disconnectBtn" class="disconnect" onclick="disconnect()" disabled>断开连接</button>
        </div>
        
        <div class="message-area" id="messages"></div>
        
        <div class="input-area">
            <input type="text" id="messageInput" placeholder="输入消息..." onkeypress="if(event.key === 'Enter') sendMessage()">
            <button class="send" onclick="sendMessage()">发送</button>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3 id="msgCount">0</h3>
                <p>消息总数</p>
            </div>
            <div class="stat-card">
                <h3 id="uptime">0s</h3>
                <p>运行时间</p>
            </div>
        </div>
    </div>
    
    <script>
        let ws = null;
        let clientId = 'client_' + Math.random().toString(36).substr(2, 9);
        let isConnected = false;
        let startTime = null;
        let uptimeInterval = null;
        let msgCount = 0;
        
        document.getElementById('clientId').textContent = 'Client ID: ' + clientId;
        
        function addMessage(content, type) {
            const messagesDiv = document.getElementById('messages');
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${type}`;
            
            const parsed = typeof content === 'string' ? JSON.parse(content) : content;
            const time = new Date(parsed.timestamp || Date.now()).toLocaleTimeString();
            
            msgDiv.innerHTML = `<strong>${type === 'sent' ? '您' : '服务器'} ${time}</strong><br>${parsed.content || content}`;
            messagesDiv.appendChild(msgDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            
            if (type === 'sent' || type === 'received') {
                msgCount++;
                document.getElementById('msgCount').textContent = msgCount;
            }
        }
        
        function updateUptime() {
            if (startTime) {
                const elapsed = Math.floor((Date.now() - startTime) / 1000);
                document.getElementById('uptime').textContent = elapsed + 's';
            }
        }
        
        function connect() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const url = `${protocol}//${window.location.host}/ws/${clientId}`;
            
            ws = new WebSocket(url);
            
            ws.onopen = function() {
                isConnected = true;
                startTime = Date.now();
                uptimeInterval = setInterval(updateUptime, 1000);
                
                document.getElementById('connectionStatus').className = 'status connected';
                document.getElementById('connectionStatus').textContent = '已连接';
                document.getElementById('connectBtn').disabled = true;
                document.getElementById('disconnectBtn').disabled = false;
                
                addMessage(`成功连接到服务器！`, 'received');
            };
            
            ws.onclose = function() {
                isConnected = false;
                clearInterval(uptimeInterval);
                
                document.getElementById('connectionStatus').className = 'status disconnected';
                document.getElementById('connectionStatus').textContent = '未连接';
                document.getElementById('connectBtn').disabled = false;
                document.getElementById('disconnectBtn').disabled = true;
                
                addMessage('连接已断开', 'received');
            };
            
            ws.onmessage = function(event) {
                addMessage(event.data, 'received');
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                addMessage('连接错误', 'received');
            };
        }
        
        function disconnect() {
            if (ws) {
                ws.close();
            }
        }
        
        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            if (!isConnected) {
                alert('请先连接到服务器！');
                return;
            }
            
            ws.send(JSON.stringify({ content: message }));
            addMessage(message, 'sent');
            input.value = '';
        }
        
        // 页面关闭时断开连接
        window.addEventListener('beforeunload', disconnect);
    </script>
</body>
</html>
    """, media_type="text/html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
