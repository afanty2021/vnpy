import api from './request'

export const strategyApi = {
  // 获取策略列表
  async getStrategies() {
    return api.get('/strategy')
  },

  // 获取策略详情
  async getStrategy(name) {
    return api.get(`/strategy/${name}`)
  },

  // 启动策略
  async startStrategy(name) {
    return api.post(`/strategy/${name}/start`)
  },

  // 停止策略
  async stopStrategy(name) {
    return api.post(`/strategy/${name}/stop`)
  },

  // 设置策略参数
  async setStrategyParam(name, paramName, value) {
    return api.put(`/strategy/${name}/param`, {
      parameter_name: paramName,
      value: value
    })
  },

  // 获取策略参数
  async getStrategyParams(name) {
    return api.get(`/strategy/${name}/params`)
  }
}
