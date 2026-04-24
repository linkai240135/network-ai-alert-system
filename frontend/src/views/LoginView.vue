<template>
  <div class="login-page">
    <div class="login-bg-grid"></div>
    <div class="login-bg-glow login-bg-glow-1"></div>
    <div class="login-bg-glow login-bg-glow-2"></div>

    <section class="login-card">
      <div class="login-card-inner">
        <div class="login-logo-wrap">
          <div class="login-logo">AI</div>
        </div>
        <h1 class="login-title">通信网络异常检测与智能告警系统</h1>
        <p class="login-subtitle">NETWORK AI ALERT SYSTEM</p>

        <div class="login-divider"></div>

        <el-form label-position="top" :model="form" @submit.prevent="handleLogin" class="login-form">
          <el-form-item>
            <el-input v-model="form.username" placeholder="用户名" prefix-icon="User" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="form.password" type="password" placeholder="密码" prefix-icon="Lock" show-password />
          </el-form-item>
          <el-button class="login-btn" type="primary" :loading="loading" @click="handleLogin">
            <span v-if="!loading">进入系统</span>
            <span v-else>验证中...</span>
          </el-button>
        </el-form>

        <p class="login-hint">默认账号 admin / admin123</p>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import { useAuthStore } from '../stores/auth'
import { getRoleLandingPath } from '../utils/roleLanding'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const handleLogin = async () => {
  loading.value = true
  try {
    const user = await authStore.login(form)
    ElMessage.success('登录成功')
    router.replace(getRoleLandingPath(user?.role))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #020b18;
  position: relative;
  overflow: hidden;
}

.login-bg-grid {
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 212, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.05) 1px, transparent 1px);
  background-size: 40px 40px;
  pointer-events: none;
}

.login-bg-glow {
  position: fixed;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
}

.login-bg-glow-1 {
  width: 600px;
  height: 600px;
  background: rgba(0, 212, 255, 0.06);
  top: -200px;
  left: -200px;
}

.login-bg-glow-2 {
  width: 500px;
  height: 500px;
  background: rgba(123, 47, 255, 0.08);
  bottom: -150px;
  right: -150px;
}

.login-card {
  position: relative;
  z-index: 1;
  width: 420px;
  background: rgba(4, 18, 48, 0.85);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-top: 1px solid rgba(0, 212, 255, 0.4);
  border-radius: 8px;
  box-shadow: 0 0 60px rgba(0, 212, 255, 0.08), 0 40px 80px rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(20px);
  overflow: hidden;
}

.login-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.8), rgba(123, 47, 255, 0.6), transparent);
}

.login-card-inner {
  padding: 40px 36px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.login-logo-wrap {
  margin-bottom: 20px;
}

.login-logo {
  width: 64px;
  height: 64px;
  border-radius: 8px;
  background: rgba(0, 212, 255, 0.08);
  border: 1px solid rgba(0, 212, 255, 0.4);
  display: grid;
  place-items: center;
  font-size: 20px;
  font-weight: 800;
  color: #00d4ff;
  letter-spacing: 0.06em;
  box-shadow: 0 0 24px rgba(0, 212, 255, 0.3), inset 0 0 20px rgba(0, 212, 255, 0.05);
  text-shadow: 0 0 12px rgba(0, 212, 255, 0.8);
}

.login-title {
  margin: 0;
  font-size: 16px;
  font-weight: 700;
  color: #e8f4ff;
  text-align: center;
  letter-spacing: 0.04em;
  line-height: 1.5;
}

.login-subtitle {
  margin: 8px 0 0;
  font-size: 11px;
  color: rgba(0, 212, 255, 0.45);
  letter-spacing: 0.2em;
  text-transform: uppercase;
}

.login-divider {
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.3), transparent);
  margin: 24px 0;
}

.login-form {
  width: 100%;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 16px;
}

.login-form :deep(.el-input__wrapper) {
  background: rgba(2, 12, 30, 0.8) !important;
  border: 1px solid rgba(0, 212, 255, 0.2) !important;
  border-radius: 4px !important;
  height: 44px;
}

.login-form :deep(.el-input__wrapper:hover) {
  border-color: rgba(0, 212, 255, 0.4) !important;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  border-color: rgba(0, 212, 255, 0.7) !important;
  box-shadow: 0 0 12px rgba(0, 212, 255, 0.2) !important;
}

.login-form :deep(.el-input__inner) {
  color: #e8f4ff !important;
  font-size: 14px;
}

.login-form :deep(.el-input__prefix-inner .el-icon) {
  color: rgba(0, 212, 255, 0.5);
}

.login-btn {
  width: 100%;
  height: 44px !important;
  margin-top: 8px;
  border-radius: 4px !important;
  background: rgba(0, 212, 255, 0.12) !important;
  border: 1px solid rgba(0, 212, 255, 0.5) !important;
  color: #00d4ff !important;
  font-size: 15px !important;
  font-weight: 600 !important;
  letter-spacing: 0.1em;
  transition: all 0.2s ease !important;
}

.login-btn:hover {
  background: rgba(0, 212, 255, 0.22) !important;
  box-shadow: 0 0 24px rgba(0, 212, 255, 0.4) !important;
}

.login-hint {
  margin: 20px 0 0;
  font-size: 12px;
  color: rgba(0, 212, 255, 0.3);
  letter-spacing: 0.06em;
}
</style>
