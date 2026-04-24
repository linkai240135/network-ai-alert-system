<template>
  <div class="layout-shell" :style="layoutStyle" :class="{ 'layout-shell-compact': isCompactViewport }">
    <aside class="sidebar" :class="{ 'sidebar-collapsed': isCollapsed }">
      <button
        class="sidebar-toggle"
        type="button"
        :title="isCollapsed ? '展开菜单栏' : '收起菜单栏'"
        @click="toggleSidebar"
      >
        {{ isCollapsed ? '>' : '<' }}
      </button>

      <div class="brand-panel">
        <div class="brand-block" :class="{ 'brand-block-collapsed': isCollapsed }">
          <div class="brand-logo">NA</div>
          <div v-if="!isCollapsed" class="brand-copy">
            <h1>网络异常检测平台</h1>
          </div>
        </div>
      </div>

      <el-menu :default-active="route.path" router class="sidebar-menu" :collapse="isCollapsed">
        <el-menu-item v-for="item in menuItems" :key="item.index" :index="item.index">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>
    </aside>

    <div
      v-if="!isCompactViewport"
      class="sidebar-resizer"
      :class="{ dragging: isDragging }"
      title="拖拽调整菜单栏宽度"
      @mousedown="startResize"
    >
      <span></span>
    </div>

    <main class="main-panel" :class="{ 'main-panel-fixed': !showTopbar }">
      <header v-if="showTopbar" class="topbar">
        <div class="topbar-title">
          <div class="topbar-breadcrumb">控制台 / {{ route.meta.title }}</div>
          <h2>{{ route.meta.title }}</h2>
        </div>

        <div class="topbar-tags">
          <span class="status-chip user-chip">管理员</span>
          <el-switch
            v-model="isDark"
            inline-prompt
            active-text="暗"
            inactive-text="亮"
            @change="handleThemeChange"
          />
          <el-button size="small" type="danger" plain @click="handleLogout">退出登录</el-button>
        </div>
      </header>

      <section
        class="workspace-shell"
        :class="{
          'workspace-shell-expanded': !showTopbar,
          'workspace-shell-fixed': !showTopbar,
        }"
      >
        <RouterView />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '../stores/auth'
import { useThemeStore } from '../stores/theme'

const SIDEBAR_WIDTH_KEY = 'network-ai-sidebar-width'
const SIDEBAR_COLLAPSED_KEY = 'network-ai-sidebar-collapsed'
const SIDEBAR_MIN_WIDTH = 220
const SIDEBAR_MAX_WIDTH = 420
const SIDEBAR_COLLAPSED_WIDTH = 96
const COMPACT_BREAKPOINT = 1180

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const themeStore = useThemeStore()

const sidebarWidth = ref(308)
const isCollapsed = ref(false)
const isDragging = ref(false)
const viewportWidth = ref(typeof window === 'undefined' ? 1440 : window.innerWidth)

const menuItems = [
  { index: '/dashboard', label: '安全运营大屏', icon: 'DataAnalysis' },
  { index: '/ai-center', label: 'AI 研判中心', icon: 'Opportunity' },
  { index: '/datasets', label: '数据集管理', icon: 'Files' },
  { index: '/training', label: '模型训练中心', icon: 'TrendCharts' },
  { index: '/detection', label: '在线检测', icon: 'Promotion' },
  { index: '/batch-detection', label: 'CSV 批量检测', icon: 'UploadFilled' },
  { index: '/alerts', label: '告警中心', icon: 'Bell' },
  { index: '/incidents', label: '事件处置中心', icon: 'Management' },
  { index: '/assets', label: '资产画像中心', icon: 'Monitor' },
  { index: '/settings', label: '系统设置', icon: 'Setting' },
]

const isDark = computed({
  get: () => themeStore.mode === 'dark',
  set: (value) => themeStore.apply(value ? 'dark' : 'light'),
})

const isCompactViewport = computed(() => viewportWidth.value <= COMPACT_BREAKPOINT)
const showTopbar = computed(() => !route.meta?.hideTopbar)

const effectiveSidebarWidth = computed(() => {
  if (isCompactViewport.value) return 0
  return isCollapsed.value ? SIDEBAR_COLLAPSED_WIDTH : sidebarWidth.value
})

const layoutStyle = computed(() => {
  if (isCompactViewport.value) return {}
  return {
    gridTemplateColumns: `${effectiveSidebarWidth.value}px 14px minmax(0, 1fr)`,
  }
})

const clampSidebarWidth = (value) => Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, value))

const persistSidebarState = () => {
  localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth.value))
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, isCollapsed.value ? '1' : '0')
}

const toggleSidebar = () => {
  if (isCompactViewport.value) return
  isCollapsed.value = !isCollapsed.value
  persistSidebarState()
}

const stopResize = () => {
  isDragging.value = false
  window.removeEventListener('mousemove', handleResize)
  window.removeEventListener('mouseup', stopResize)
  document.body.classList.remove('sidebar-resizing')
  persistSidebarState()
}

const handleResize = (event) => {
  if (!isDragging.value) return
  const nextWidth = clampSidebarWidth(event.clientX - 18)
  sidebarWidth.value = nextWidth
  if (isCollapsed.value && nextWidth > SIDEBAR_COLLAPSED_WIDTH + 24) {
    isCollapsed.value = false
  }
}

const startResize = () => {
  if (isCompactViewport.value) return
  isDragging.value = true
  isCollapsed.value = false
  document.body.classList.add('sidebar-resizing')
  window.addEventListener('mousemove', handleResize)
  window.addEventListener('mouseup', stopResize)
}

const handleViewportResize = () => {
  viewportWidth.value = window.innerWidth
}

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}

const handleThemeChange = (value) => {
  themeStore.apply(value ? 'dark' : 'light')
}

onMounted(() => {
  const cachedWidth = Number(localStorage.getItem(SIDEBAR_WIDTH_KEY) || '')
  const cachedCollapsed = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)

  if (Number.isFinite(cachedWidth) && cachedWidth > 0) {
    sidebarWidth.value = clampSidebarWidth(cachedWidth)
  }
  if (cachedCollapsed === '1') {
    isCollapsed.value = true
  }

  window.addEventListener('resize', handleViewportResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleViewportResize)
  stopResize()
})
</script>
