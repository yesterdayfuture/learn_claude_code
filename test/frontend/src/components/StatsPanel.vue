<script setup>
import { computed } from 'vue'

const props = defineProps({
  stats: {
    type: Object,
    default: () => ({
      activeConnections: 0,
      totalClientsToday: 0,
      status: 'running'
    })
  }
})

defineEmits(['refresh'])

const statusColor = computed(() => {
  const statusMap = {
    running: 'success',
    warning: 'warning',
    error: 'danger',
    stopped: 'info'
  }
  return statusMap[props.stats.status] || 'info'
})
</script>

<template>
  <div class="stats-panel">
    <div class="panel-header">
      <h2>系统状态</h2>
      <el-button 
        size="small" 
        :icon="Refresh" 
        circle 
        @click="$emit('refresh')"
      />
    </div>
    
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon connection-icon">
          <el-icon><Connection /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.activeConnections }}</div>
          <div class="stat-label">活跃连接</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon client-icon">
          <el-icon><User /></el-icon>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.totalClientsToday }}</div>
          <div class="stat-label">今日访客</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon status-icon">
          <el-icon v-if="stats.status === 'running'"><CircleCheck /></el-icon>
          <el-icon v-else-if="stats.status === 'warning'"><Warning /></el-icon>
          <el-icon v-else><Close /></el-icon>
        </div>
        <div class="stat-info">
          <el-tag :type="statusColor" size="small">
            {{ stats.status }}
          </el-tag>
          <div class="stat-label">服务状态</div>
        </div>
      </div>
    </div>
    
    <div class="panel-footer">
      <el-progress 
        :percentage="(stats.activeConnections / 100 * 100).toFixed(1)" 
        :format="(v) => `当前负载 ${v}%"`
      />
    </div>
  </div>
</template>

<style scoped>
.stats-panel {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.panel-header h2 {
  font-size: 1.1rem;
  color: #303133;
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 15px;
  margin-bottom: 15px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin-right: 12px;
}

.connection-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.client-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.status-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 0.8rem;
  color: #909399;
}

.panel-footer {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px solid #eee;
}
</style>
