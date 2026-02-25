import api from './request'

export const authApi = {
  // 登录
  async login(username, password) {
    return api.post('/auth/login', { username, password })
  },

  // 登出
  async logout() {
    return api.post('/auth/logout')
  },

  // 刷新令牌
  async refreshToken(refreshToken) {
    return api.post('/auth/refresh', { refresh_token: refreshToken })
  },

  // 获取当前用户信息
  async getCurrentUser() {
    return api.get('/auth/me')
  }
}
