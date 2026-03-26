<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import axios from 'axios'
import ConnectionCard from '../components/ConnectionCard.vue'
import ConnectionList from '../components/ConnectionList.vue'
import StatsPanel from '../components/StatsPanel.vue'

// State
const ws = ref(null)
const isConnecting = ref(false)
const isConnected = ref(false)
const messages = ref([])
const newMessage = ref('')
const clientInfo = ref({
  clientId: '',
  connectTime: null,
  messageCount: 0
})

const connections = ref([])
const stats = ref({
  activeConnections: 0,
  totalClientsToday: 0,
  status: 'running'
})
const logs = ref([])

// WebSocket URL
const WS_URL = 'ws://localhost:8000/ws/'

// Computed properties
const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}

const getWebSocketUrl = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const hostname = window.location.hostname
  const port = window.location.port || '8000'
  const clientId = clientInfo.value.clientId
  return `${protocol}//${hostname}:${port}/ws/${clientId}`
}

// Methods
const generateClientId = () => {
  return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
}

const connect = async () => {
  if (isConnecting.value || isConnected.value) return
  
  isConnecting.value = true
  clientInfo.value.clientId = generateClientId()
  
  try {
    const wsUrl = getWebSocketUrl()
    console.log(`Connecting to ${wsUrl}...`)
    
    ws.value = new WebSocket(wsUrl)
    
    ws.value.onopen = () => {
      isConnected.value = true
      isConnecting.value = false
      clientInfo.value.connectTime = new Date()
      addSystemMessage('✅ 成功连接到服务器！')
      ElNotification({
        title: '连接成功',
        message: `Client ID: ${clientInfo.value.clientId}`,
        type: 'success',
        duration: 3000
      })
      
      // Refresh connection stats
      fetchStats()
      fetchLogs()
    }
    
    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'welcome') {
          addSystemMessage(`欢迎消息：${data.content}`)
        } else if (data.type === 'response') {
          addMessage(data, 'received')
        } else {
          addMessage(data, 'received')
        }
      } catch (e) {
        addSystemMessage(`收到原始消息：${event.data}`)
      }
    }
    
    ws.value.onclose = () => {
      disconnectUI()
      addSystemMessage('❌ 连接已断开')
      ElNotification({
        title: '连接断开',
        message: 'WebSocket 连接已关闭',
        type: 'warning'
      })
    }
    
    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
      isConnecting.value = false
      addSystemMessage('⚠️ 连接错误')
      ElNotification({
        title: '连接错误',
        message: '无法连接到 WebSocket 服务器',
        type: 'error'
      })
    }
    
  } catch (error) {
    console.error('Connect error:', error)
    isConnecting.value = false
    ElMessage.error('连接失败：' + error.message)
  }
}

const disconnect = () => {
  if (ws.value) {
    ws.value.close()
    disconnectUI()
    addSystemMessage('👋 已手动断开连接')
  }
}

const disconnectUI = () => {
  isConnected.value = false
  isConnecting.value = false
  ws.value = null
}

const sendMessage = () => {
  if (!newMessage.value.trim()) return
  if (!isConnected.value) {
    ElMessage.warning('请先连接到服务器')
    return
  }
  
  const messageData = {
    content: newMessage.value.trim(),
    timestamp: new Date().toISOString()
  }
  
  ws.value.send(JSON.stringify(messageData))
  addMessage(messageData, 'sent')
  newMessage.value = ''
  clientInfo.value.messageCount++
}

const addMessage = (data, type) => {
  messages.value.push({
    ...data,
    type: type,
    id: Date.now()
  })
  
  // Keep only last 100 messages
  if (messages.value.length > 100) {
    messages.value = messages.value.slice(-100)
  }
}

const addSystemMessage = (content) => {
  messages.value.push({
    content,
    type: 'system',
    timestamp: new Date().toISOString(),
    id: Date.now()
  })
}

const fetchConnections = async () => {
  try {
    const response = await axios.get('/api/connections')
    if (response.data.success) {
      connections.value = response.data.data
    }
  } catch (error) {
    console.error('Failed to fetch connections:', error)
  }
}

const fetchStats = async () => {
  try {
    const response = await axios.get('/api/stats')
    if (response.data.success) {
      stats.value = response.data.data
    }
  } catch (error) {
    console.error('Failed to fetch stats:', error)
  }
}

const fetchLogs = async () => {
  try {
    const response = await axios.get('/api/logs?limit=50')
    if (response.data.success) {
      logs.value = response.data.data
    }
  } catch (error) {
    console.error('Failed to fetch logs:', error)
  }
}

const broadcastMessage = async (message) => {
  try {
    const response = await axios.post('/api/message/broadcast', {
      message: message,
      type: 'broadcast'
    })
    if (response.data.success) {
      ElMessage.success(`消息已广播到 ${response.data.recipient_count} 个客户端`)
    }
  } catch (error) {
    ElMessage.error('广播失败：' + error.message)
  }
}

// Lifecycle
onMounted(() => {
  // Initial data load
  fetchStats()
  fetchConnections()
  fetchLogs()
  
  // Auto-refresh every 5 seconds when connected
  setInterval(() => {
    if (isConnected.value) {
      fetchConnections()
    }
  }, 5000)
})
</script>

<template>
  <div class="home-view">
    <!-- Header -->
    <header class="page-header">
      <h1>🔗 WebSocket 连接管理中心</h1>
      <p>实时监控和管理 WebSocket 连接状态</p>
    </header>
    
    <div class="main-content">
      <!-- Left Panel: Connection Control -->
      <section class="panel panel-left">
        <div class="connection-control">
          <h2>连接控制</h2>
          
          <div class="status-bar">
            <el-tag :type="isConnected ? 'success' : 'danger'" size="large" effect="dark">
              {{ isConnected ? '● 已连接' : '○ 未连接' }}
            </el-tag>
            <span v-if="clientInfo.clientId" class="client-id">
              Client ID: {{ clientInfo.clientId }}
            </span>
          </div>
          
          <div class="connection-stats">
            <el-statistic title="连接时间" :value="formatTime(clientInfo.connectTime)" />
            <el-statistic title="消息数量" :value="clientInfo.messageCount" />
          </div>
          
          <div class="action-buttons">
            <el-button 
              :loading="isConnecting" 
              :disabled="isConnected"
              @click="connect"
              type="success"
              size="large"
            >
              {{ isConnecting ? '连接中...' : '连接服务器' }}
            </el-button>
            
            <el-button 
              :disabled="!isConnected" 
              @click="disconnect"
              type="danger"
              size="large"
            >
              断开连接
            </el-button>
          </div>
        </div>
        
        <!-- Message Area -->
        <div class="message-section">
          <h2>消息历史</h2>
          <div class="messages-container" ref="messagesContainer">
            <div 
              v-for="msg in messages" 
              :key="msg.id"
              class="message-item"
              :class="['message-' + msg.type]"
            >
              <span class="message-time">{{ formatTime(msg.timestamp) }}</span>
              <span class="message-content">{{ msg.content }}</span>
            </div>
          </div>
          
          <div class="message-input">
            <el-input
              v-model="newMessage"
              placeholder="输入消息..."
              :disabled="!isConnected"
              @keydown.enter="sendMessage"
            >
              <template #append>
                <el-button :icon="null" @click="sendMessage">发送</el-button>
              </template>
            </el-input>
          </div>
        </div>
      </section>
      
      <!-- Right Panel: System Status -->
      <section class="panel panel-right">
        <!-- Stats Panel -->
        <StatsPanel :stats="stats" @refresh="fetchStats" />
        
        <!-- Connection List -->
        <ConnectionList :connections="connections" />
        
        <!-- Logs -->
        <div class="logs-section">
          <h2>系统日志</h2>
          <el-timeline>
            <el-timeline-item
              v-for="(log, index) in logs.slice().reverse()"
              :key="index"
              :timestamp="formatTime(log.timestamp)"
              :type="log.event === 'connect' ? 'success' : log.event === 'disconnect' ? 'info' : 'primary'"
              placement="top"
            >
              <el-card shadow="hover">
                <p><strong>{{ log.client_id }}</strong>: {{ log.message }}</p>
              </el-card>
            </el-timeline-item>
          </el-timeline>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 20px;
}

.page-header {
  text-align: center;
  margin-bottom: 30px;
  color: #2c3e50;
}

.page-header h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
}

.page-header p {
  font-size: 1.1rem;
  color: #666;
}

.main-content {
  display: grid;
  grid-template-columns: 1fr 400px;
  gap: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

/* Tablet and smaller desktop */
@media (max-width: 1200px) {
  .main-content {
    grid-template-columns: 1fr;
  }
  
  .page-header h1 {
    font-size: 2rem;
  }
}

/* Mobile phones */
@media (max-width: 768px) {
  .home-view {
    padding: 15px;
  }
  
  .page-header {
    margin-bottom: 20px;
  }
  
  .page-header h1 {
    font-size: 1.8rem;
  }
  
  .page-header p {
    font-size: 1rem;
  }
  
  .panel {
    padding: 15px;
  }
  
  .status-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    padding: 12px;
  }
  
  .connection-stats {
    grid-template-columns: 1fr;
    gap: 10px;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 10px;
  }
  
  .action-buttons .el-button {
    width: 100%;
  }
  
  .messages-container {
    height: 250px;
    padding: 12px;
  }
  
  .message-item {
    padding: 8px 12px;
    margin: 6px 0;
  }
  
  .message-time {
    font-size: 0.75rem;
  }
  
  .logs-section h2 {
    font-size: 1.2rem;
  }
}

/* Small mobile phones */
@media (max-width: 480px) {
  .home-view {
    padding: 10px;
  }
  
  .page-header h1 {
    font-size: 1.5rem;
  }
  
  .page-header p {
    font-size: 0.9rem;
  }
  
  .panel {
    padding: 12px;
    border-radius: 8px;
  }
  
  .messages-container {
    height: 200px;
    padding: 10px;
  }
  
  .message-content {
    font-size: 0.9rem;
  }
  
  .client-id {
    font-size: 0.8rem;
  }
}

.panel {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.connection-control {
  margin-bottom: 30px;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
}

.client-id {
  font-family: monospace;
  color: #666;
  font-size: 0.9rem;
}

.connection-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.action-buttons {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.message-section {
  border-top: 1px solid #eee;
  padding-top: 20px;
}

.messages-container {
  height: 300px;
  overflow-y: auto;
  border: 1px solid #e1e1e1;
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 15px;
  background: #fafafa;
}

.message-item {
  padding: 10px 15px;
  margin: 8px 0;
  border-radius: 8px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-sent {
  background: #d4edda;
  border-left: 4px solid #28a745;
  text-align: right;
}

.message-received {
  background: #e7f3ff;
  border-left: 4px solid #007bff;
}

.message-system {
  background: #fff3cd;
  border-left: 4px solid #ffc107;
  text-align: center;
  font-style: italic;
}

.message-time {
  font-size: 0.8rem;
  color: #888;
  display: block;
  margin-bottom: 4px;
}

.logs-section {
  margin-top: 20px;
}

/* Accessibility improvements */
.home-view * {
  /* Ensure sufficient contrast for text */
}

.message-item:focus {
  outline: 2px solid #409eff;
  outline-offset: 2px;
}

.el-button:focus,
.el-input:focus-within {
  outline: 2px solid #409eff;
  outline-offset: 2px;
}

/* Screen reader only class */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
