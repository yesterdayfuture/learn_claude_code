<script setup>
defineProps({
  connections: {
    type: Array,
    default: () => []
  }
})

const formatTime = (timestamp) => {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}
</script>

<template>
  <div class="connection-list">
    <h2>活跃连接</h2>
    
    <el-empty v-if="connections.length === 0" description="暂无活跃连接" />
    
    <el-table v-else :data="connections" stripe border size="small">
      <el-table-column prop="client_id" label="Client ID" min-width="120">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.client_id }}</el-tag>
        </template>
      </el-table-column>
      
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-icon><VideoPlay /></el-icon>
        </template>
      </el-table-column>
      
      <el-table-column prop="connected_at" label="连接时间" width="100">
        <template #default="{ row }">
          {{ formatTime(row.connected_at) }}
        </template>
      </el-table-column>
    </el-table>
    
    <div class="list-footer">
      <span>共 {{ connections.length }} 个连接</span>
    </div>
  </div>
</template>

<style scoped>
.connection-list {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-top: 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

h2 {
  font-size: 1.1rem;
  color: #303133;
  margin-bottom: 15px;
}

.list-footer {
  text-align: right;
  margin-top: 10px;
  font-size: 0.875rem;
  color: #909399;
}
</style>
