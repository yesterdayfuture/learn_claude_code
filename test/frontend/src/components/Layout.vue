<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const isCollapse = ref(false)
const isMobile = ref(false)
const sidebarActive = ref(false)

// Check if device is mobile
const checkIsMobile = () => {
  isMobile.value = window.innerWidth <= 768
}

// Handle resize events
onMounted(() => {
  checkIsMobile()
  window.addEventListener('resize', checkIsMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkIsMobile)
})

// Toggle sidebar for mobile
const toggleSidebar = () => {
  if (isMobile.value) {
    sidebarActive.value = !sidebarActive.value
  } else {
    isCollapse.value = !isCollapse.value
  }
}

// Close sidebar when clicking outside (mobile only)
const handleClickOutside = (event) => {
  if (isMobile.value && sidebarActive.value) {
    const sidebar = document.querySelector('.sidebar')
    const menuButton = document.querySelector('.header-left .el-button')
    if (sidebar && !sidebar.contains(event.target) && menuButton && !menuButton.contains(event.target)) {
      sidebarActive.value = false
    }
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <el-container class="layout-container">
    <!-- Sidebar Navigation -->
    <el-aside 
      :width="isCollapse && !isMobile ? '64px' : '200px'" 
      class="sidebar" 
      :class="{ 'active': sidebarActive }"
    >
      <div class="logo-area">
        <h1 v-if="!(isCollapse && !isMobile) || isMobile">WebSocket Manager</h1>
        <span v-else>WM</span>
      </div>
      
      <el-menu
        :default-active="$route.path"
        :collapse="isCollapse && !isMobile"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
        router
        @select="() => { if (isMobile) sidebarActive = false }"
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
            :icon="isCollapse && !isMobile ? Expand : Fold" 
            circle 
            @click="toggleSidebar"
            aria-label="Toggle sidebar navigation"
          />
          <span class="page-title">{{ (isCollapse && !isMobile) ? '' : 'WebSocket 连接管理中心' }}</span>
        </div>
        
        <div class="header-right">
          <el-badge :value="1" class="item">
            <el-button :icon="Bell" circle aria-label="Notifications" />
          </el-badge>
          <el-avatar :size="32" src="https://cube.elemecdn.com/0/88/03b0d39583f48206768a7534e55bcpng.png" alt="User avatar" />
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
  display: flex;
}

.sidebar {
  background-color: #304156;
  transition: width 0.3s ease;
  height: 100vh;
  position: relative;
  z-index: 100;
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
  height: 60px;
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
  flex: 1;
}

.main-footer {
  background: white;
  text-align: center;
  color: #909399;
  font-size: 0.875rem;
  border-top: 1px solid #ebeef5;
  padding: 10px 0;
}

/* Tablet */
@media (max-width: 1024px) {
  .sidebar {
    width: 64px !important;
  }
  
  .logo-area h1 {
    display: none;
  }
  
  .el-menu-item span {
    display: none;
  }
  
  .el-sub-menu__title span {
    display: none;
  }
}

/* Mobile phones */
@media (max-width: 768px) {
  .page-title {
    display: none;
  }
  
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 200px !important;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    z-index: 1000;
  }
  
  .sidebar.active {
    transform: translateX(0);
  }
  
  .logo-area h1 {
    display: block;
  }
  
  .el-menu-item span {
    display: inline;
  }
  
  .main-header {
    padding: 0 15px;
  }
  
  .header-left .el-button {
    margin-right: 10px;
  }
  
  .main-content {
    padding: 15px;
  }
}

/* Small mobile phones */
@media (max-width: 480px) {
  .main-header {
    padding: 0 10px;
    height: 50px;
  }
  
  .header-right .el-badge,
  .header-right .el-avatar {
    transform: scale(0.8);
  }
  
  .main-content {
    padding: 10px;
  }
  
  .main-footer {
    font-size: 0.8rem;
    padding: 8px 0;
  }
}

/* Accessibility improvements */
.el-menu-item:focus,
.el-button:focus {
  outline: 2px solid #409eff;
  outline-offset: 2px;
}

.el-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1) !important;
}

/* Ensure sufficient contrast */
.sidebar .el-menu {
  background-color: #304156 !important;
  border-right: none !important;
}

.sidebar .el-menu-item {
  color: #bfcbd9 !important;
}

.sidebar .el-menu-item.is-active {
  color: #409eff !important;
  background-color: rgba(64, 158, 255, 0.1) !important;
}
</style>
