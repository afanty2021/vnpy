import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  async (error) => {
    const authStore = useAuthStore()

    if (error.response) {
      const { status, data } = error.response

      // 处理401未授权错误
      if (status === 401) {
        // 尝试刷新令牌
        const refreshed = await authStore.refreshAccessToken()
        if (refreshed) {
          // 重试原请求
          return api.request(error.config)
        } else {
          // 跳转到登录页
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
        }
      }

      // 显示错误消息
      const message = data?.message || data?.detail || '请求失败'
      ElMessage.error(message)

      return Promise.reject(new Error(message))
    }

    if (error.request) {
      ElMessage.error('网络错误，请检查网络连接')
      return Promise.reject(error)
    }

    ElMessage.error('请求配置错误')
    return Promise.reject(error)
  }
)

export default api
