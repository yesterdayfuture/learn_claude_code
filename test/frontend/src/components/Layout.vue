<script setup>
import { ref } from 'vue'
const isCollapse = ref(false)
</script>

<template>
  <el-container class="layout-container">
    <!-- Sidebar Navigation -->
    <el-aside :width="isCollapse ? '64px' : '200px'" class="sidebar">
      <div class="logo-area">
        <h1 v-if="!isCollapse">WebSocket Manager</h1>
        <span v-else>WM</span>
      </div>
      
      <el-menu
        :default-active="'/'"
        :collapse="isCollapse"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        router
      >
        <el-menu-item index="/">
          <el-icon><Connection /></el-icon>
          <span>连接管理</span>
        </el-menu-item>
        
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>系统设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <!-- Main Content -->
    <el-container>
      <!-- Header -->
      <el-header class="main-header">
        <div class="header-left">
          <el-button 
            :icon="isCollapse ? Expand : Fold" 
            circle 
            @click="isCollapse = !isCollapse"
          />
          <span class="page-title">{{ isCollapse ? '' : 'WebSocket 连接管理中心' }}</span>
        </div>
        
        <div class="header-right">
          <el-badge :value="1" class="item">
            <el-button :icon="Bell" circle />
          </el-badge>
          <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" />
        </div>
      </el-header>
      
      <!-- Main View -->
      <el-main class="main-content">
        <router-view />
      </el-main>
      
      <!-- Footer -->
      <el-footer class="main-footer">
        <p>© 2024 WebSocket Connection Manager | Version 1.0.0</p>
      </el-footer>
    </el-container>
  </el-container>
</template>

<style scoped>
.layout-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  transition: width 0.3s ease;
}

.logo-area {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-area h1 {
  font-size: 1.2rem;
}

.main-header {
  background: white;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.page-title {
  font-size: 1.2rem;
  font-weight: 500;
  color: #303133;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.main-content {
  background: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}

.main-footer {
  background: white;
  text-align: center;
  color: #909399;
  font-size: 0.875rem;
  border-top: 1px solid #ebeef5;
}

@media (max-width: 768px) {
  .page-title {
    display: none;
  }
  
  .sidebar {
    position: fixed;
    z-index: 1000;
  }
}
</style>
