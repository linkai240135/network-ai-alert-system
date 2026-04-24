import { defineStore } from 'pinia'

import { loginApi, logoutApi, meApi } from '../api/auth'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.user,
  },
  actions: {
    async fetchMe() {
      try {
        const response = await meApi()
        this.user = response.data.user
      } catch {
        this.user = null
      }
      return this.user
    },
    async login(payload) {
      await loginApi(payload)
      const user = await this.fetchMe()
      if (!user) {
        throw new Error('登录态未生效，请重试')
      }
      return user
    },
    async logout() {
      await logoutApi()
      this.user = null
    },
  },
})
