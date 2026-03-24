import { defineStore } from 'pinia'

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    isConnected: false,
    clientId: null,
    ws: null,
    messages: [],
    connections: [],
    stats: {
      activeConnections: 0,
      totalClientsToday: 0,
      status: 'running'
    },
    logs: []
  }),

  getters: {
    getActiveConnectionCount: (state) => state.connections.length,
    isOnline: (state) => state.stats.status === 'running'
  },

  actions: {
    async connect(clientId) {
      try {
        this.clientId = clientId
        
        // WebSocket connection logic would go here
        return true
      } catch (error) {
        console.error('Connection failed:', error)
        return false
      }
    },

    disconnect() {
      if (this.ws) {
        this.ws.close()
        this.ws = null
      }
      this.isConnected = false
    },

    addMessage(message) {
      this.messages.push({
        ...message,
        id: Date.now(),
        timestamp: new Date().toISOString()
      })
      
      // Keep only last 100 messages
      if (this.messages.length > 100) {
        this.messages = this.messages.slice(-100)
      }
    },

    clearMessages() {
      this.messages = []
    },

    updateStats(stats) {
      this.stats = stats
    },

    updateConnections(connections) {
      this.connections = connections
    },

    addLog(log) {
      this.logs.push(log)
      
      if (this.logs.length > 50) {
        this.logs = this.logs.slice(-50)
      }
    }
  }
})
