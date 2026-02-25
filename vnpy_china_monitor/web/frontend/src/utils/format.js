import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import relativeTime from 'dayjs/plugin/relativeTime'
import duration from 'dayjs/plugin/duration'

dayjs.locale('zh-cn')
dayjs.extend(relativeTime)
dayjs.extend(duration)

// 格式化日期时间
export function formatDateTime(timestamp, format = 'YYYY-MM-DD HH:mm:ss') {
  if (!timestamp) return '-'
  return dayjs(timestamp).format(format)
}

// 格式化相对时间
export function formatRelativeTime(timestamp) {
  if (!timestamp) return '-'
  return dayjs(timestamp).fromNow()
}

// 格式化金额
export function formatMoney(value, decimals = 2) {
  if (value === null || value === undefined) return '-'
  return Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

// 格式化数量
export function formatVolume(value) {
  if (value === null || value === undefined) return '-'

  if (Math.abs(value) >= 100000000) {
    return (value / 100000000).toFixed(2) + '亿'
  } else if (Math.abs(value) >= 10000) {
    return (value / 10000).toFixed(2) + '万'
  }

  return value.toLocaleString()
}

// 格式化百分比
export function formatPercent(value, decimals = 2) {
  if (value === null || value === undefined) return '-'
  return value.toFixed(decimals) + '%'
}

// 格式化价格变化
export function formatPriceChange(change, decimals = 2) {
  if (change === null || change === undefined) return { text: '-', class: '' }

  const sign = change >= 0 ? '+' : ''
  const className = change > 0 ? 'text-up' : change < 0 ? 'text-down' : ''
  return {
    text: sign + change.toFixed(decimals),
    class: className
  }
}

// 获取价格颜色类
export function getPriceColorClass(value, base = 0) {
  if (value === null || value === undefined) return ''
  if (value > base) return 'text-up'
  if (value < base) return 'text-down'
  return ''
}

// 获取方向颜色类
export function getDirectionColorClass(direction) {
  if (direction === '多' || direction === 'long' || direction === 'buy') {
    return 'text-up'
  } else if (direction === '空' || direction === 'short' || direction === 'sell') {
    return 'text-down'
  }
  return ''
}

// 格式化合约代码
export function formatSymbol(vtSymbol) {
  if (!vtSymbol) return '-'

  // 简单的格式化，可以根据实际需求调整
  const parts = vtSymbol.split('.')
  if (parts.length > 1) {
    return parts[0]
  }
  return vtSymbol
}

// 获取合约类型
export function getSymbolType(vtSymbol) {
  if (!vtSymbol) return 'unknown'

  if (vtSymbol.includes('SHFE') || vtSymbol.includes('SH')) {
    return 'futures'
  } else if (vtSymbol.includes('SZSE') || vtSymbol.includes('SZ')) {
    return 'stock'
  } else if (vtSymbol.includes('CFFEX')) {
    return 'index'
  }

  return 'unknown'
}

// 计算持仓盈亏
export function calculatePositionPnl(entryPrice, currentPrice, volume, direction) {
  if (!entryPrice || !currentPrice || !volume) return 0

  const priceDiff = direction === '多'
    ? currentPrice - entryPrice
    : entryPrice - currentPrice

  return priceDiff * volume
}

// 格式化持仓信息
export function formatPositionInfo(position) {
  return {
    symbol: formatSymbol(position.vt_symbol),
    direction: position.direction,
    volume: position.volume,
    available: position.available || position.volume,
    price: formatMoney(position.price),
    pnl: formatMoney(position.pnl || 0),
    pnlClass: getPriceColorClass(position.pnl || 0)
  }
}

// 格式化委托信息
export function formatOrderInfo(order) {
  return {
    symbol: formatSymbol(order.vt_symbol),
    direction: order.direction,
    type: order.type,
    volume: order.volume,
    traded: order.traded || 0,
    price: formatMoney(order.price),
    status: order.status,
    statusClass: getOrderStatusClass(order.status)
  }
}

// 获取委托状态颜色类
export function getOrderStatusClass(status) {
  const statusMap = {
    '全部成交': 'text-success',
    '部分成交': 'text-warning',
    '未成交': 'text-info',
    '已撤销': 'text-muted',
    '拒单': 'text-danger'
  }
  return statusMap[status] || ''
}

// 防抖函数
export function debounce(fn, delay = 300) {
  let timer = null
  return function (...args) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  }
}

// 节流函数
export function throttle(fn, delay = 300) {
  let lastTime = 0
  return function (...args) {
    const now = Date.now()
    if (now - lastTime >= delay) {
      fn.apply(this, args)
      lastTime = now
    }
  }
}

// 深拷贝
export function deepClone(obj) {
  if (obj === null || typeof obj !== 'object') return obj
  if (obj instanceof Date) return new Date(obj)
  if (obj instanceof Array) return obj.map(item => deepClone(item))

  const clonedObj = {}
  for (const key in obj) {
    if (obj.hasOwnProperty(key)) {
      clonedObj[key] = deepClone(obj[key])
    }
  }
  return clonedObj
}

// 生成唯一ID
export function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}
