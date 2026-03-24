# WebSocket 连接管理中心

一个基于 **FastAPI** 后端和 **Vue.js** 前端的实时 WebSocket 连接管理系统。支持多客户端连接管理、消息收发测试、连接状态监控等功能。

## 🎯 项目特点

- ⚡ **高性能异步架构** - 基于 FastAPI + Uvicorn 的异步 WebSocket 服务
- 🔗 **实时双向通信** - 支持客户端与服务器之间的实时消息传递
- 👥 **多连接管理** - 可同时管理多个 WebSocket 客户端连接
- 📊 **实时监控面板** - 可视化展示连接状态、统计信息和系统日志
- 💬 **消息广播功能** - 支持向所有连接客户端发送广播消息
- 🛡️ **错误边界保护** - 前端具备错误捕获和处理机制
- ⚙️ **配置可定制** - 提供系统设置界面，支持个性化配置

## 📁 项目结构

```
test/
├── backend/                    # FastAPI 后端服务
│   ├── main.py                 # 主入口文件（包含 API 路由和 WebSocket 端点）
│   └── requirements.txt        # Python 依赖包列表
│
├── frontend/                   # Vue.js 前端应用
│   ├── public/
│   │   └── favicon.svg         # 网站图标
│   ├── src/
│   │   ├── components/         # Vue 组件目录
│   │   │   ├── ConnectionCard.vue    # 连接卡片组件
│   │   │   ├── ConnectionList.vue    # 连接列表组件
│   │   │   ├── StatsPanel.vue        # 统计面板组件
│   │   │   ├── Layout.vue            # 布局组件
│   │   │   └── ErrorBoundary.vue     # 错误边界组件
│   │   ├── router/
│   │   │   └── index.js          # Vue Router 路由配置
│   │   ├── views/
│   │   │   ├── HomeView.vue        # 主页视图（连接管理）
│   │   │   └── SettingsView.vue    # 设置页面视图
│   │   ├── store/
│   │   │   └── index.js          # Pinia 状态管理
│   │   ├── App.vue               # 根组件
│   │   └── main.js               # 应用入口文件
│   ├── index.html               # HTML 模板
│   ├── package.json             # NPM 依赖包列表
│   └── vite.config.js           # Vite 构建配置
│
└── README.md                    # 项目说明文档
```

## ✨ 功能特性

### 核心功能
| 功能 | 描述 |
|------|------|
| WebSocket 连接 | 建立和维护长连接，支持实时双向通信 |
| 连接管理 | 查看当前所有活跃连接及其状态 |
| 消息收发 | 发送和接收消息，支持 Echo 模式测试 |
| 广播消息 | 向所有连接客户端发送广播消息 |
| 连接日志 | 记录连接的创建、断开和消息事件 |
| 统计分析 | 展示活跃连接数、访客数、服务状态等 |

### 界面功能
| 模块 | 功能 |
|------|------|
| 连接控制 | 一键连接/断开，显示 Client ID 和连接时间 |
| 消息历史 | 滚动查看消息记录，区分发送/接收/系统消息 |
| 系统状态 | 实时更新服务状态和负载情况 |
| 连接列表 | 表格化展示所有活跃连接信息 |
| 系统日志 | 时间轴方式展示系统事件日志 |
| 设置页面 | 配置自动连接、重连策略、主题语言等 |

## 🚀 快速开始

### 环境要求

- **Python** 3.8+
- **Node.js** 16+
- **npm** 或 **yarn**

### 安装与运行

#### 1. 启动后端服务

```bash
# 进入后端目录
cd test/backend

# 安装依赖
pip install -r requirements.txt

# 启动服务（开发模式，支持热重载）
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

或者直接运行：
```bash
python main.py
```

#### 2. 启动前端应用

```bash
# 进入前端目录
cd test/frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

#### 3. 访问应用

| 服务 | 地址 |
|------|------|
| 后端 API | http://localhost:8000 |
| 后端文档 | http://localhost:8000/docs |
| 前端界面 | http://localhost:5173 |
| WebSocket 测试页 | http://localhost:8000/websocket-test |

## 🔌 API 接口说明

### RESTful API

| 方法 | 路径 | 描述 |
|------|------|------|
| `GET` | `/api/connections` | 获取所有活跃连接列表 |
| `POST` | `/api/message/broadcast` | 向所有连接广播消息 |
| `GET` | `/api/stats` | 获取系统统计信息 |
| `GET` | `/api/logs` | 获取连接日志 |

### WebSocket API

| 协议 | 路径 | 描述 |
|------|------|------|
| `ws` | `/ws/{client_id}` | 建立 WebSocket 连接 |

### 消息格式

**客户端发送：**
```json
{
  "content": "Hello, Server!"
}
```

**服务器响应：**
```json
{
  "type": "response",
  "content": "Echo: Hello, Server!",
  "client_id": "client_xxxxxxxx",
  "timestamp": "2024-01-01T12:00:00"
}
```

## 🛠️ 技术栈

### 后端技术
| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | ^0.104 | Web 框架，提供 RESTful 和 WebSocket 支持 |
| Uvicorn | ^0.24 | ASGI 服务器，高性能异步 |
| Pydantic | ^2.5 | 数据验证和序列化 |
| Starlette | ^0.27 | ASGI 工具库 |

### 前端技术
| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | ^3.4 | 渐进式 JavaScript 框架 |
| Vite | ^5.0 | 下一代前端构建工具 |
| Element Plus | ^2.4 | 桌面端 UI 组件库 |
| Pinia | ^2.1 | Vue 官方状态管理库 |
| Vue Router | ^4.2 | 单页面应用路由 |
| Axios | ^1.6 | HTTP 客户端 |

## 📝 使用示例

### 1. 连接 WebSocket

打开前端界面后，点击「连接服务器」按钮即可建立连接。

### 2. 发送消息

在连接成功后，在消息输入框中输入内容并按回车或点击「发送」按钮。

### 3. 广播消息

后端可通过调用 `/api/message/broadcast` 接口向所有客户端广播消息。

### 4. 查看日志

在右侧面板可查看实时的系统日志，包括连接建立、断开和消息收发记录。

## 🐛 常见问题

**Q: 前端无法连接到后端？**  
A: 确保后端服务已启动，检查 `vite.config.js` 中的 proxy 配置是否正确指向后端地址。

**Q: WebSocket 连接失败？**  
A: 检查浏览器控制台是否有 CORS 错误，确认后端允许跨域请求。

**Q: 如何部署到生产环境？**  
A: 
- 前端：运行 `npm run build` 生成静态文件
- 后端：使用 gunicorn 配合 uvicorn  worker 运行

## 📄 许可证

MIT License

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

---

<div align="center">
<strong>Made with ❤️ using FastAPI & Vue.js</strong>
</div>
