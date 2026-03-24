<script setup>
import { ref } from 'vue'

defineProps({
  connection: Object,
  modelValue: Boolean
})

const selected = ref(false)
defineEmits(['update:modelValue'])
</script>

<template>
  <el-card shadow="hover" class="connection-card" :class="{ 'is-selected': modelValue }">
    <div class="card-header">
      <span class="client-id">{{ connection?.client_id }}</span>
      <el-tag size="small" type="success">{{ connection?.status }}</el-tag>
    </div>
    
    <div class="card-body">
      <div class="info-row">
        <span class="label">连接时间:</span>
        <span class="value">{{ connection?.connected_at || '-' }}</span>
      </div>
      
      <div class="info-row">
        <span class="label">消息数:</span>
        <span class="value">{{ connection?.messageCount || 0 }}</span>
      </div>
    </div>
    
    <div class="card-footer">
      <el-button size="small" plain type="danger" @click="$emit('disconnect')">
        断开
      </el-button>
      <el-button size="small" plain type="primary" @click="$emit('send')">
        发送消息
      </el-button>
    </div>
  </el-card>
</template>

<style scoped>
.connection-card {
  margin-bottom: 15px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.connection-card.is-selected {
  border-color: #409eff;
  background-color: #ecf5ff;
}

.connection-card:hover {
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.client-id {
  font-family: monospace;
  font-size: 0.9rem;
  color: #606266;
}

.card-body {
  padding: 10px 0;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px dashed #ebeef5;
}

.info-row:last-child {
  border-bottom: none;
}

.label {
  color: #909399;
  font-size: 0.875rem;
}

.value {
  color: #303133;
  font-weight: 500;
}

.card-footer {
  display: flex;
  gap: 10px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
  margin-top: 10px;
}
</style>
