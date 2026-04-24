<template>
  <div class="login-page">
    <section class="login-card login-card-simple">
      <div class="login-card-header-simple">
        <div class="login-brand">NA</div>
        <h1>通信网络异常检测与智能告警系统</h1>
        <h2>管理员登录</h2>
      </div>

      <el-form label-position="top" :model="form" @submit.prevent="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="密码" show-password />
        </el-form-item>
        <el-button class="full-width" type="primary" :loading="loading" @click="handleLogin">进入系统</el-button>
      </el-form>
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
