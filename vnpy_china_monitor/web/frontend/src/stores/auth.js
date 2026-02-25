import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token') || '')
  const user = ref(null)
  const refreshToken = ref(localStorage.getItem('refresh_token') || '')

  const isLoggedIn = computed(() => !!token.value)

  async function login(username, password) {
    try {
      const response = await authApi.login(username, password)
      token.value = response.access_token
      refreshToken.value = response.refresh_token
      user.value = response.user

      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)

      return true
    } catch (error) {
      console.error('登录失败:', error)
      return false
    }
  }

  async function logout() {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('登出失败:', error)
    } finally {
      token.value = ''
      refreshToken.value = ''
      user.value = null

      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }

  async function refreshAccessToken() {
    try {
      const response = await authApi.refreshToken(refreshToken.value)
      token.value = response.access_token

      localStorage.setItem('access_token', response.access_token)

      return true
    } catch (error) {
      console.error('刷新令牌失败:', error)
      await logout()
      return false
    }
  }

  async function getUserInfo() {
    try {
      const response = await authApi.getCurrentUser()
      user.value = response
      return response
    } catch (error) {
      console.error('获取用户信息失败:', error)
      return null
    }
  }

  return {
    token,
    user,
    refreshToken,
    isLoggedIn,
    login,
    logout,
    refreshAccessToken,
    getUserInfo
  }
})
