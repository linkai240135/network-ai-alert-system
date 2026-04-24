import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '../layout/AppLayout.vue'
import AlertsView from '../views/AlertsView.vue'
import AiCenterView from '../views/AiCenterView.vue'
import AssetView from '../views/AssetView.vue'
import BatchDetectionView from '../views/BatchDetectionView.vue'
import DashboardView from '../views/DashboardView.vue'
import DatasetView from '../views/DatasetView.vue'
import DetectionView from '../views/DetectionView.vue'
import IncidentView from '../views/IncidentView.vue'
import LoginView from '../views/LoginView.vue'
import SettingsView from '../views/SettingsView.vue'
import TrainingView from '../views/TrainingView.vue'
import { pinia } from '../stores'
import { useAuthStore } from '../stores/auth'
import { getRoleLandingPath } from '../utils/roleLanding'

const routes = [
  { path: '/login', component: LoginView, meta: { title: '登录' } },
  {
    path: '/',
    component: AppLayout,
    redirect: '/dashboard',
    children: [
      { path: '/dashboard', component: DashboardView, meta: { title: '安全运营大屏' } },
      { path: '/ai-center', component: AiCenterView, meta: { title: 'AI 智能研判中心', hideTopbar: true } },
      { path: '/datasets', component: DatasetView, meta: { title: '数据集管理' } },
      { path: '/training', component: TrainingView, meta: { title: '模型训练中心' } },
      { path: '/detection', component: DetectionView, meta: { title: '在线检测' } },
      { path: '/batch-detection', component: BatchDetectionView, meta: { title: 'CSV 批量检测' } },
      { path: '/alerts', component: AlertsView, meta: { title: '告警中心' } },
      { path: '/incidents', component: IncidentView, meta: { title: '事件处置中心' } },
      { path: '/assets', component: AssetView, meta: { title: '资产画像中心' } },
      { path: '/settings', component: SettingsView, meta: { title: '系统设置' } },
    ],
  },
  { path: '/display', redirect: '/dashboard' },
  { path: '/display/dashboard', redirect: '/dashboard' },
  { path: '/display/assets', redirect: '/assets' },
  { path: '/ops', redirect: '/alerts' },
  { path: '/ops/alerts', redirect: '/alerts' },
  { path: '/ops/incidents', redirect: '/incidents' },
  { path: '/ops/ai-center', redirect: '/ai-center' },
  { path: '/ops/detection', redirect: '/detection' },
  { path: '/admin', redirect: '/training' },
  { path: '/admin/datasets', redirect: '/datasets' },
  { path: '/admin/training', redirect: '/training' },
  { path: '/admin/batch-detection', redirect: '/batch-detection' },
  { path: '/admin/assets', redirect: '/assets' },
  { path: '/admin/role-permissions', redirect: '/settings' },
  { path: '/admin/settings', redirect: '/settings' },
  { path: '/role-permissions', redirect: '/settings' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)

  if (to.path === '/login') {
    if (authStore.user) return getRoleLandingPath(authStore.user?.role)
    return true
  }

  if (!authStore.user) {
    await authStore.fetchMe()
  }

  if (!authStore.user) {
    return '/login'
  }

  return true
})

export default router
