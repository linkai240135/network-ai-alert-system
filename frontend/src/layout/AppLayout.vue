<template>
  <div class="layout-shell">
    <nav class="topnav">
      <div class="topnav-logo">
        <div class="topnav-logo-icon">AI</div>
        <div class="topnav-logo-text">
          <span class="topnav-logo-name">网络异常检测平台</span>
          <span class="topnav-logo-sub">NETWORK AI ALERT</span>
        </div>
      </div>

      <div class="topnav-menu">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="topnav-item"
          :class="{ 'topnav-item-active': isActive(item.path) }"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </div>

      <div class="topnav-actions">
        <span class="topnav-status">
          <span class="topnav-status-dot"></span>
          在线
        </span>
        <span class="topnav-user">管理员</span>
        <el-button size="small" type="danger" plain @click="handleLogout">退出</el-button>
      </div>
    </nav>

    <main class="main-panel">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const menuItems = [
  { path: '/dashboard', label: '大屏', icon: 'DataAnalysis' },
  { path: '/ai-center', label: 'AI研判', icon: 'Opportunity' },
  { path: '/datasets', label: '数据集', icon: 'Files' },
  { path: '/training', label: '训练', icon: 'TrendCharts' },
  { path: '/detection', label: '检测', icon: 'Promotion' },
  { path: '/batch-detection', label: '批量', icon: 'UploadFilled' },
  { path: '/alerts', label: '告警', icon: 'Bell' },
  { path: '/incidents', label: '事件', icon: 'Management' },
  { path: '/assets', label: '资产', icon: 'Monitor' },
  { path: '/settings', label: '设置', icon: 'Setting' },
]

const isActive = (path) => route.path === path || route.path.startsWith(path + '/')

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}

onMounted(() => {
  themeStore.apply('dark')
})
</script>
