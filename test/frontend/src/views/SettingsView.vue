<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const settings = ref({
  autoConnect: true,
  reconnectAttempts: 3,
  reconnectInterval: 5000,
  maxMessages: 100,
  showLogs: true,
  theme: 'light',
  language: 'zh-CN'
})

const saveSettings = () => {
  // 保存设置逻辑
  localStorage.setItem('websocket-manager-settings', JSON.stringify(settings.value))
  ElMessage.success('设置已保存')
}

const resetSettings = () => {
  settings.value = {
    autoConnect: true,
    reconnectAttempts: 3,
    reconnectInterval: 5000,
    maxMessages: 100,
    showLogs: true,
    theme: 'light',
    language: 'zh-CN'
  }
  localStorage.removeItem('websocket-manager-settings')
  ElMessage.warning('设置已重置为默认值')
}

// 加载保存的设置
try {
  const saved = localStorage.getItem('websocket-manager-settings')
  if (saved) {
    settings.value = { ...settings.value, ...JSON.parse(saved) }
  }
} catch (e) {
  console.error('Failed to load settings:', e)
}
</script>

<template>
  <div class="settings-view">
    <h1>系统设置</h1>
    
    <el-card shadow="never">
      <template #header>
        <span>连接配置</span>
      </template>
      
      <el-form :model="settings" label-width="140px">
        <el-form-item label="自动连接">
          <el-switch v-model="settings.autoConnect" />
        </el-form-item>
        
        <el-form-item label="重连次数">
          <el-slider v-model="settings.reconnectAttempts" :min="0" :max="10" :step="1" />
          <span>{{ settings.reconnectAttempts }} 次</span>
        </el-form-item>
        
        <el-form-item label="重连间隔">
          <el-slider v-model="settings.reconnectInterval" :min="1000" :max="30000" :step="1000" 
                     format-tooltip="value ms" />
          <span>{{ settings.reconnectInterval / 1000 }} 秒</span>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card shadow="never" style="margin-top: 20px;">
      <template #header>
        <span>消息配置</span>
      </template>
      
      <el-form :model="settings" label-width="140px">
        <el-form-item label="最大消息数">
          <el-input-number v-model="settings.maxMessages" :min="10" :max="1000" />
          <span>条</span>
        </el-form-item>
        
        <el-form-item label="显示日志">
          <el-switch v-model="settings.showLogs" />
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-card shadow="never" style="margin-top: 20px;">
      <template #header>
        <span>界面设置</span>
      </template>
      
      <el-form :model="settings" label-width="140px">
        <el-form-item label="主题">
          <el-radio-group v-model="settings.theme">
            <el-radio-button label="light">浅色</el-radio-button>
            <el-radio-button label="dark">深色</el-radio-button>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item label="语言">
          <el-select v-model="settings.language" placeholder="请选择语言">
            <el-option label="简体中文" value="zh-CN" />
            <el-option label="English" value="en-US" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>
    
    <div class="button-group">
      <el-button type="primary" @click="saveSettings">
        保存设置
      </el-button>
      <el-button @click="resetSettings">
        重置为默认
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.settings-view {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

h1 {
  color: #303133;
  margin-bottom: 20px;
}

.el-form {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.el-form-item__label {
  line-height: 36px !important;
}

.button-group {
  margin-top: 30px;
  text-align: center;
}

.button-group .el-button {
  margin: 0 10px;
}
</style>
