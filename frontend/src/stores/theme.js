import { defineStore } from 'pinia'

const STORAGE_KEY = 'network-ai-theme'

export const useThemeStore = defineStore('theme', {
  state: () => ({
    mode: localStorage.getItem(STORAGE_KEY) || 'light',
  }),
  actions: {
    apply(mode = this.mode) {
      this.mode = mode
      document.documentElement.setAttribute('data-theme', mode)
      localStorage.setItem(STORAGE_KEY, mode)
    },
    toggle() {
      this.apply(this.mode === 'light' ? 'dark' : 'light')
    },
  },
})
