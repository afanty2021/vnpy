import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { alertApi } from '@/api/alert'
import { useWebSocket } from '@/utils/websocket'

export const useAlertStore = defineStore('alert', () => {
  const alerts = ref([])
  const stats = ref(null)
  const loading = ref(false)

  let wsClient = null

  function initWebSocket(clientId) {
    wsClient = useWebSocket(clientId)

    wsClient.on('alert', (data) => {
      alerts.value.unshift(data)
    })

    return wsClient
  }

  async function fetchAlerts(options = {}) {
    loading.value = true
    try {
      const data = await alertApi.getAlerts(options)
      alerts.value = data.alerts || []
    } catch (error) {
      console.error('获取告警列表失败:', error)
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      stats.value = await alertApi.getAlertStats()
    } catch (error) {
      console.error('获取告警统计失败:', error)
    }
  }

  async function acknowledgeAlert(alertId, comment = '') {
    try {
      await alertApi.acknowledgeAlert(alertId, comment)
      const alert = alerts.value.find(a => a.id === alertId)
      if (alert) {
        alert.acknowledged = true
        alert.acknowledged_at = new Date().toISOString()
        alert.acknowledged_by = 'current_user'
        alert.acknowledgment_comment = comment
      }
      return true
    } catch (error) {
      console.error('确认告警失败:', error)
      return false
    }
  }

  const activeAlerts = computed(() => {
    return alerts.value.filter(a => !a.acknowledged)
  })

  const criticalAlerts = computed(() => {
    return activeAlerts.value.filter(a => a.severity === 'critical')
  })

  const warningAlerts = computed(() => {
    return activeAlerts.value.filter(a => a.severity === 'warning')
  })

  const infoAlerts = computed(() => {
    return activeAlerts.value.filter(a => a.severity === 'info')
  })

  function getAlertsBySeverity(severity) {
    return alerts.value.filter(a => a.severity === severity)
  }

  function getAlertsBySource(source) {
    return alerts.value.filter(a => a.source === source)
  }

  function getRecentAlerts(limit = 10) {
    return alerts.value.slice(0, limit)
  }

  return {
    alerts,
    stats,
    loading,
    activeAlerts,
    criticalAlerts,
    warningAlerts,
    infoAlerts,
    initWebSocket,
    fetchAlerts,
    fetchStats,
    acknowledgeAlert,
    getAlertsBySeverity,
    getAlertsBySource,
    getRecentAlerts
  }
})
