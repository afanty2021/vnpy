import api from './request'

export const alertApi = {
  // 获取告警列表
  async getAlerts(options = {}) {
    const params = {}
    if (options.active !== undefined) params.active = options.active
    if (options.severity) params.severity = options.severity
    if (options.source) params.source = options.source
    if (options.limit) params.limit = options.limit
    return api.get('/alerts', { params })
  },

  // 获取告警统计
  async getAlertStats() {
    return api.get('/alerts/stats')
  },

  // 确认告警
  async acknowledgeAlert(alertId, comment = '') {
    return api.post(`/alerts/${alertId}/acknowledge`, { comment })
  }
}
