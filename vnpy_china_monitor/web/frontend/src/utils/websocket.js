import { ref, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

class WebSocketClient {
  constructor(url) {
    this.url = url
    this.ws = null
    this.reconnectTimer = null
    this.heartbeatTimer = null
    this.reconnectDelay = 5000
    this.heartbeatInterval = 30000
    this.handlers = new Map()
    this.isConnected = ref(false)
  }

  connect() {
    try {
      this.ws = new WebSocket(this.url)

      this.ws.onopen = () => {
        console.log('WebSocket连接成功')
        this.isConnected.value = true
        this.startHeartbeat()

        // 订阅默认主题
        this.send('subscribe', { topics: ['tick', 'order', 'position', 'account', 'alert'] })
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('解析WebSocket消息失败:', error)
        }
      }

      this.ws.onclose = () => {
        console.log('WebSocket连接关闭')
        this.isConnected.value = false
        this.stopHeartbeat()
        this.scheduleReconnect()
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error)
      }
    } catch (error) {
      console.error('WebSocket连接失败:', error)
      this.scheduleReconnect()
    }
  }

  disconnect() {
    this.stopHeartbeat()
    this.clearReconnectTimer()

    if (this.ws) {
      this.ws.close()
      this.ws = null
    }

    this.isConnected.value = false
  }

  send(type, data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }))
    } else {
      console.warn('WebSocket未连接，无法发送消息')
    }
  }

  on(eventType, handler) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, [])
    }
    this.handlers.get(eventType).push(handler)
  }

  off(eventType, handler) {
    if (this.handlers.has(eventType)) {
      const handlers = this.handlers.get(eventType)
      const index = handlers.indexOf(handler)
      if (index !== -1) {
        handlers.splice(index, 1)
      }
    }
  }

  handleMessage(message) {
    const { type, data } = message

    if (this.handlers.has(type)) {
      this.handlers.get(type).forEach(handler => {
        try {
          handler(data)
        } catch (error) {
          console.error(`处理${type}消息失败:`, error)
        }
      })
    }

    // 处理心跳响应
    if (type === 'pong') {
      // 心跳响应处理
    }
  }

  startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      this.send('ping', {})
    }, this.heartbeatInterval)
  }

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  scheduleReconnect() {
    this.clearReconnectTimer()

    this.reconnectTimer = setTimeout(() => {
      console.log('尝试重新连接WebSocket...')
      this.connect()
    }, this.reconnectDelay)
  }

  clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }
}

let wsInstance = null

export function useWebSocket(clientId) {
  if (!wsInstance) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = import.meta.env.VITE_WS_HOST || window.location.host
    const url = `${protocol}//${host}/ws/${clientId}`

    wsInstance = new WebSocketClient(url)
    wsInstance.connect()
  }

  return wsInstance
}

export function disconnectWebSocket() {
  if (wsInstance) {
    wsInstance.disconnect()
    wsInstance = null
  }
}
