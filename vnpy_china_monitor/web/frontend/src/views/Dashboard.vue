<template>
  <div class="dashboard">
    <el-row :gutter="20">
      <!-- 账户信息 -->
      <el-col :span="6">
        <el-card class="metric-card account-card">
          <div class="metric-header">
            <span>账户余额</span>
            <el-icon color="#409eff"><Wallet /></el-icon>
          </div>
          <div class="metric-value">
            ¥{{ formatMoney(account?.balance || 0) }}
          </div>
          <div class="metric-footer">
            <span>可用: ¥{{ formatMoney(account?.available || 0) }}</span>
          </div>
        </el-card>
      </el-col>

      <!-- 持仓盈亏 -->
      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <span>持仓盈亏</span>
            <el-icon><TrendCharts /></el-icon>
          </div>
          <div class="metric-value" :class="pnlClass">
            ¥{{ formatMoney(positionPnl) }}
          </div>
          <div class="metric-footer">
            <span>持仓数: {{ positionCount }}</span>
          </div>
        </el-card>
      </el-col>

      <!-- 今日成交 -->
      <el-col :span="6">
        <el-card class="metric-card">
          <div class="metric-header">
            <span>今日成交</span>
            <el-icon><ShoppingCart /></el-icon>
          </div>
          <div class="metric-value">
            ¥{{ formatMoney(todayTurnover) }}
          </div>
          <div class="metric-footer">
            <span>笔数: {{ todayTradeCount }}</span>
          </div>
        </el-card>
      </el-col>

      <!-- 活跃告警 -->
      <el-col :span="6">
        <el-card class="metric-card" :class="{ 'has-alert': criticalAlertCount > 0 }">
          <div class="metric-header">
            <span>活跃告警</span>
            <el-icon :color="criticalAlertCount > 0 ? '#f56c6c' : ''">
              <Bell />
            </el-icon>
          </div>
          <div class="metric-value" :class="{ 'text-danger': criticalAlertCount > 0 }">
            {{ criticalAlertCount }} / {{ activeAlertCount }}
          </div>
          <div class="metric-footer">
            <span>严重 / 总计</span>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-3">
      <!-- 持仓分布 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>持仓分布</span>
              <el-button text @click="refreshPositions">刷新</el-button>
            </div>
          </template>
          <PositionPieChart :data="positionData" />
        </el-card>
      </el-col>

      <!-- 策略状态 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>策略状态</span>
              <el-button text @click="refreshStrategies">刷新</el-button>
            </div>
          </template>
          <StrategyStatusChart :data="strategyData" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-3">
      <!-- 实时行情 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>实时行情</span>
              <el-select
                v-model="selectedSymbol"
                placeholder="选择合约"
                size="small"
                style="width: 200px"
                @change="handleSymbolChange"
              >
                <el-option
                  v-for="symbol in subscribedSymbols"
                  :key="symbol"
                  :label="symbol"
                  :value="symbol"
                />
              </el-select>
            </div>
          </template>
          <MarketLineChart
            v-if="selectedSymbol"
            :vt-symbol="selectedSymbol"
          />
          <el-empty v-else description="请选择合约" />
        </el-card>
      </el-col>

      <!-- 最近告警 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近告警</span>
              <el-button text @click="$router.push('/alerts')">查看全部</el-button>
            </div>
          </template>
          <RecentAlertList :alerts="recentAlerts" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="mt-3">
      <!-- 活跃策略 -->
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>活跃策略</span>
              <el-button text @click="$router.push('/strategy')">管理策略</el-button>
            </div>
          </template>
          <ActiveStrategyTable :strategies="activeStrategies" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { formatMoney } from '@/utils/format'
import { useTradeStore } from '@/stores/trade'
import { useStrategyStore } from '@/stores/strategy'
import { useAlertStore } from '@/stores/alert'
import { useMarketStore } from '@/stores/market'
import {
  Wallet,
  TrendCharts,
  ShoppingCart,
  Bell
} from '@element-plus/icons-vue'
import PositionPieChart from '@/components/charts/PositionPieChart.vue'
import StrategyStatusChart from '@/components/charts/StrategyStatusChart.vue'
import MarketLineChart from '@/components/charts/MarketLineChart.vue'
import RecentAlertList from '@/components/dashboard/RecentAlertList.vue'
import ActiveStrategyTable from '@/components/dashboard/ActiveStrategyTable.vue'

const tradeStore = useTradeStore()
const strategyStore = useStrategyStore()
const alertStore = useAlertStore()
const marketStore = useMarketStore()

const selectedSymbol = ref(null)

// 账户信息
const account = computed(() => tradeStore.account)

// 持仓盈亏
const positionPnl = computed(() => {
  return tradeStore.positions.reduce((sum, pos) => sum + (pos.pnl || 0), 0)
})

const pnlClass = computed(() => {
  return positionPnl.value >= 0 ? 'text-up' : 'text-down'
})

const positionCount = computed(() => tradeStore.positions.length)

// 今日成交
const todayTurnover = computed(() => {
  const today = new Date().toISOString().split('T')[0]
  return tradeStore.trades
    .filter(t => t.trade_time?.startsWith(today))
    .reduce((sum, t) => sum + (t.volume * t.price), 0)
})

const todayTradeCount = computed(() => {
  const today = new Date().toISOString().split('T')[0]
  return tradeStore.trades.filter(t => t.trade_time?.startsWith(today)).length
})

// 告警统计
const activeAlertCount = computed(() => alertStore.activeAlerts.length)
const criticalAlertCount = computed(() => alertStore.criticalAlerts.length)

// 持仓分布数据
const positionData = computed(() => {
  return tradeStore.positions.map(pos => ({
    name: pos.vt_symbol,
    value: pos.volume * pos.price,
    pnl: pos.pnl || 0
  }))
})

// 策略状态数据
const strategyData = computed(() => {
  const running = strategyStore.strategies.filter(s => s.status === 'running').length
  const stopped = strategyStore.strategies.filter(s => s.status === 'stopped').length
  return { running, stopped }
})

// 活跃策略
const activeStrategies = computed(() => strategyStore.getRunningStrategies())

// 最近告警
const recentAlerts = computed(() => alertStore.getRecentAlerts(5))

// 已订阅合约
const subscribedSymbols = computed(() => Array.from(marketStore.subscribedSymbols))

function refreshPositions() {
  tradeStore.fetchPositions()
}

function refreshStrategies() {
  strategyStore.fetchStrategies()
}

function handleSymbolChange(symbol) {
  if (symbol && !marketStore.subscribedSymbols.has(symbol)) {
    marketStore.subscribeSymbol(symbol)
  }
}

onMounted(async () => {
  // 加载数据
  await Promise.all([
    tradeStore.fetchAccount(),
    tradeStore.fetchPositions(),
    tradeStore.fetchTrades(),
    strategyStore.fetchStrategies(),
    alertStore.fetchAlerts({ active: true })
  ])
})
</script>

<style scoped lang="scss">
.dashboard {
  padding: 20px;
}

.metric-card {
  &.has-alert {
    border: 2px solid #f56c6c;
  }
}

.metric-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
  color: #909399;
}

.metric-value {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 8px;
}

.metric-footer {
  font-size: 12px;
  color: #909399;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
