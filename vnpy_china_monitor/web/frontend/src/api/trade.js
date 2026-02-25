import api from './request'

export const tradeApi = {
  // 获取账户资金
  async getAccount() {
    return api.get('/trade/account')
  },

  // 获取持仓列表
  async getPositions(vtSymbol = null) {
    const params = {}
    if (vtSymbol) params.vt_symbol = vtSymbol
    return api.get('/trade/positions', { params })
  },

  // 获取委托列表
  async getOrders(vtSymbol = null) {
    const params = {}
    if (vtSymbol) params.vt_symbol = vtSymbol
    return api.get('/trade/orders', { params })
  },

  // 获取成交列表
  async getTrades(vtSymbol = null) {
    const params = {}
    if (vtSymbol) params.vt_symbol = vtSymbol
    return api.get('/trades', { params })
  },

  // 发送委托
  async sendOrder(orderRequest) {
    return api.post('/trade/order/send', orderRequest)
  },

  // 撤销委托
  async cancelOrder(vtOrderid) {
    return api.post('/trade/order/cancel', { vt_orderid: vtOrderid })
  }
}
