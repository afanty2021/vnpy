import { defineStore } from 'pinia'
import { ref } from 'vue'
import { marketApi } from '@/api/market'
import { useWebSocket } from '@/utils/websocket'

export const useMarketStore = defineStore('market', () => {
  const ticks = ref(new Map())
  const subscribedSymbols = ref(new Set())
  const historyBars = ref(new Map())

  let wsClient = null

  function initWebSocket(clientId) {
    wsClient = useWebSocket(clientId)

    wsClient.on('market_tick', (data) => {
      ticks.value.set(data.vt_symbol, data)
    })

    return wsClient
  }

  function subscribeSymbol(vtSymbol) {
    if (subscribedSymbols.value.has(vtSymbol)) return

    subscribedSymbols.value.add(vtSymbol)
    wsClient?.send('subscribe', { topic: `tick:${vtSymbol}` })

    marketApi.subscribe(vtSymbol)
  }

  function unsubscribeSymbol(vtSymbol) {
    if (!subscribedSymbols.value.has(vtSymbol)) return

    subscribedSymbols.value.delete(vtSymbol)
    wsClient?.send('unsubscribe', { topic: `tick:${vtSymbol}` })

    marketApi.unsubscribe(vtSymbol)
  }

  async function getTick(vtSymbol) {
    if (ticks.value.has(vtSymbol)) {
      return ticks.value.get(vtSymbol)
    }

    try {
      const tick = await marketApi.getTick(vtSymbol)
      ticks.value.set(vtSymbol, tick)
      return tick
    } catch (error) {
      console.error('获取行情失败:', error)
      return null
    }
  }

  async function getHistoryBars(vtSymbol, interval, start, end) {
    const key = `${vtSymbol}_${interval}_${start}_${end}`

    if (historyBars.value.has(key)) {
      return historyBars.value.get(key)
    }

    try {
      const bars = await marketApi.getHistoryBars(vtSymbol, interval, start, end)
      historyBars.value.set(key, bars)
      return bars
    } catch (error) {
      console.error('获取K线数据失败:', error)
      return []
    }
  }

  function getTickValue(vtSymbol) {
    return ticks.value.get(vtSymbol)
  }

  function getAllTicks() {
    return Array.from(ticks.value.values())
  }

  function clear() {
    ticks.value.clear()
    subscribedSymbols.value.clear()
    historyBars.value.clear()
  }

  return {
    ticks,
    subscribedSymbols,
    historyBars,
    initWebSocket,
    subscribeSymbol,
    unsubscribeSymbol,
    getTick,
    getTickValue,
    getAllTicks,
    getHistoryBars,
    clear
  }
})
