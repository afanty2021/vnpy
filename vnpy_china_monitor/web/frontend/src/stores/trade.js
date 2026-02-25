import { defineStore } from 'pinia'
import { ref } from 'vue'
import { tradeApi } from '@/api/trade'

export const useTradeStore = defineStore('trade', () => {
  const account = ref(null)
  const positions = ref([])
  const orders = ref([])
  const trades = ref([])
  const loading = ref(false)

  async function fetchAccount() {
    loading.value = true
    try {
      account.value = await tradeApi.getAccount()
    } catch (error) {
      console.error('获取账户信息失败:', error)
    } finally {
      loading.value = false
    }
  }

  async function fetchPositions() {
    loading.value = true
    try {
      positions.value = await tradeApi.getPositions()
    } catch (error) {
      console.error('获取持仓失败:', error)
    } finally {
      loading.value = false
    }
  }

  async function fetchOrders() {
    loading.value = true
    try {
      orders.value = await tradeApi.getOrders()
    } catch (error) {
      console.error('获取委托失败:', error)
    } finally {
      loading.value = false
    }
  }

  async function fetchTrades() {
    loading.value = true
    try {
      trades.value = await tradeApi.getTrades()
    } catch (error) {
      console.error('获取成交失败:', error)
    } finally {
      loading.value = false
    }
  }

  async function sendOrder(orderRequest) {
    try {
      const order = await tradeApi.sendOrder(orderRequest)
      orders.value.unshift(order)
      return order
    } catch (error) {
      console.error('发送委托失败:', error)
      throw error
    }
  }

  async function cancelOrder(vtOrderid) {
    try {
      await tradeApi.cancelOrder(vtOrderid)
      const index = orders.value.findIndex(o => o.vt_orderid === vtOrderid)
      if (index !== -1) {
        orders.value[index].status = '已撤销'
      }
    } catch (error) {
      console.error('撤销委托失败:', error)
      throw error
    }
  }

  function updateAccount(accountData) {
    account.value = accountData
  }

  function updatePosition(positionData) {
    const index = positions.value.findIndex(p => p.vt_positionid === positionData.vt_positionid)
    if (index !== -1) {
      positions.value[index] = positionData
    } else {
      positions.value.push(positionData)
    }
  }

  function updateOrder(orderData) {
    const index = orders.value.findIndex(o => o.vt_orderid === orderData.vt_orderid)
    if (index !== -1) {
      orders.value[index] = orderData
    } else {
      orders.value.unshift(orderData)
    }
  }

  function addTrade(tradeData) {
    trades.value.unshift(tradeData)
  }

  function getPositionSummary() {
    const summary = {
      long: { count: 0, volume: 0, pnl: 0 },
      short: { count: 0, volume: 0, pnl: 0 },
      net: { volume: 0, pnl: 0 }
    }

    positions.value.forEach(pos => {
      const direction = pos.direction === '多' ? 'long' : 'short'
      summary[direction].count += 1
      summary[direction].volume += pos.volume
      summary[direction].pnl += pos.pnl || 0
      summary.net.volume += pos.volume * (pos.direction === '多' ? 1 : -1)
      summary.net.pnl += pos.pnl || 0
    })

    return summary
  }

  return {
    account,
    positions,
    orders,
    trades,
    loading,
    fetchAccount,
    fetchPositions,
    fetchOrders,
    fetchTrades,
    sendOrder,
    cancelOrder,
    updateAccount,
    updatePosition,
    updateOrder,
    addTrade,
    getPositionSummary
  }
})
