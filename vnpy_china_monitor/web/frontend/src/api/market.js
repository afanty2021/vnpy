import api from './request'

export const marketApi = {
  // 获取实时行情
  async getTick(vtSymbol) {
    return api.get(`/market/tick/${vtSymbol}`)
  },

  // 获取所有行情
  async getAllTicks() {
    return api.get('/market/ticks')
  },

  // 获取K线数据
  async getHistoryBars(vtSymbol, interval = '1m', start = null, end = null) {
    const params = { interval }
    if (start) params.start = start
    if (end) params.end = end
    return api.get(`/market/bars/${vtSymbol}`, { params })
  },

  // 订阅行情
  async subscribe(vtSymbol) {
    return api.post('/market/subscribe', { vt_symbol: vtSymbol })
  },

  // 取消订阅
  async unsubscribe(vtSymbol) {
    return api.delete(`/market/subscribe/${vtSymbol}`)
  },

  // 获取已订阅列表
  async getSubscribed() {
    return api.get('/market/subscribed')
  }
}
