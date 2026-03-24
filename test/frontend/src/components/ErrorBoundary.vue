<script setup>
// Simple error boundary component for Vue 3
defineProps({
  fallback: [String, Object]
})
</script>

<script>
export default {
  data() {
    return {
      hasError: false,
      errorMessage: ''
    }
  },
  
  methods: {
    componentDidCatch(error, errorInfo) {
      this.hasError = true;
      this.errorMessage = error.message || 'Unknown error';
    },
    
    retryRender() {
      this.hasError = false;
      this.errorMessage = '';
    }
  }
}
</script>

<template>
  <div v-if="hasError" class="error-boundary">
    <div class="error-content">
      <el-icon type="danger" size="large">
        <el-icon><ExclamationFilled /></el-icon>
      </el-icon>
      <h2>哎呀，出错了！</h2>
      <p>{{ errorMessage }}</p>
      <el-button @click="retryRender">重试</el-button>
    </div>
  </div>
  
  <div v-else>
    <slot></slot>
  </div>
</template>

<style scoped>
.error-boundary {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}

.error-content {
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  max-width: 500px;
}

.error-content h2 {
  color: #606266;
  margin: 20px 0 10px 0;
}

.el-icon-large {
  font-size: 48px;
  color: #ff99ac;
}
</style>
