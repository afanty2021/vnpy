import { defineStore } from 'pinia'
import { ref } from 'vue'
import { strategyApi } from '@/api/strategy'

export const useStrategyStore = defineStore('strategy', () => {
  const strategies = ref([])
  const loading = ref(false)

  async function fetchStrategies() {
    loading.value = true
    try {
      const data = await strategyApi.getStrategies()
      strategies.value = data.strategies || []
    } catch (error) {
      console.error('获取策略列表失败:', error)
    } finally {
      loading.value = false
    }
  }

  async function getStrategy(name) {
    try {
      return await strategyApi.getStrategy(name)
    } catch (error) {
      console.error('获取策略详情失败:', error)
      return null
    }
  }

  async function startStrategy(name) {
    try {
      await strategyApi.startStrategy(name)
      const strategy = strategies.value.find(s => s.name === name)
      if (strategy) {
        strategy.status = 'running'
      }
      return true
    } catch (error) {
      console.error('启动策略失败:', error)
      return false
    }
  }

  async function stopStrategy(name) {
    try {
      await strategyApi.stopStrategy(name)
      const strategy = strategies.value.find(s => s.name === name)
      if (strategy) {
        strategy.status = 'stopped'
      }
      return true
    } catch (error) {
      console.error('停止策略失败:', error)
      return false
    }
  }

  async function setStrategyParam(name, paramName, value) {
    try {
      await strategyApi.setStrategyParam(name, paramName, value)
      const strategy = strategies.value.find(s => s.name === name)
      if (strategy && strategy.parameters) {
        const param = strategy.parameters.find(p => p.name === paramName)
        if (param) {
          param.value = value
        }
      }
      return true
    } catch (error) {
      console.error('设置策略参数失败:', error)
      return false
    }
  }

  async function getStrategyParams(name) {
    try {
      return await strategyApi.getStrategyParams(name)
    } catch (error) {
      console.error('获取策略参数失败:', error)
      return []
    }
  }

  function getRunningStrategies() {
    return strategies.value.filter(s => s.status === 'running')
  }

  function getStoppedStrategies() {
    return strategies.value.filter(s => s.status === 'stopped')
  }

  return {
    strategies,
    loading,
    fetchStrategies,
    getStrategy,
    startStrategy,
    stopStrategy,
    setStrategyParam,
    getStrategyParams,
    getRunningStrategies,
    getStoppedStrategies
  }
})
