<template>
  <div class="market-page">
    <el-row :gutter="20">
      <!-- 行情列表 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>行情列表</span>
              <el-input
                v-model="searchQuery"
                placeholder="搜索合约"
                size="small"
                :prefix-icon="Search"
                style="width: 200px"
              />
            </div>
          </template>
          <el-table
            :data="filteredTicks"
            height="calc(100vh - 240px)"
            @row-click="handleRowClick"
          >
            <el-table-column prop="vt_symbol" label="合约" width="120" />
            <el-table-column label="最新价" width="100">
              <template #default="{ row }">
                <span :class="getPriceClass(row.last_price, row.pre_close)">
                  {{ row.last_price?.toFixed(2) || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="涨跌幅" width="80">
              <template #default="{ row }">
                <span :class="getChangeClass(row.change_percent)">
                  {{ row.change_percent?.toFixed(2) || '-' }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="volume" label="成交量">
              <template #default="{ row }">
                {{ formatVolume(row.volume) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- K线图表 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>{{ selectedSymbol || '选择合约' }}</span>
              <div class="chart-controls">
                <el-radio-group v-model="interval" size="small" @change="handleIntervalChange">
                  <el-radio-button label="1m">1分</el-radio-button>
                  <el-radio-button label="5m">5分</el-radio-button>
                  <el-radio-button label="15m">15分</el-radio-button>
                  <el-radio-button label="1h">1时</el-radio-button>
                  <el-radio-button label="1d">日线</el-radio-button>
                </el-radio-group>
                <el-button
                  :type="isSubscribed ? 'danger' : 'primary'"
                  size="small"
                  @click="toggleSubscribe"
                >
                  {{ isSubscribed ? '取消订阅' : '订阅' }}
                </el-button>
              </div>
            </div>
          </template>
          <CandleChart
            v-if="selectedSymbol"
            :vt-symbol="selectedSymbol"
            :interval="interval"
            :height="500"
          />
          <el-empty v-else description="请选择合约查看K线图" />
        </el-card>

        <!-- 详细信息 -->
        <el-card class="mt-2">
          <template #header>
            <span>合约详情</span>
          </template>
          <el-descriptions v-if="selectedTick" :column="3" border>
            <el-descriptions-item label="合约代码">
              {{ selectedTick.vt_symbol }}
            </el-descriptions-item>
            <el-descriptions-item label="合约名称">
              {{ selectedTick.symbol }}
            </el-descriptions-item>
            <el-descriptions-item label="交易所">
              {{ selectedTick.exchange }}
            </el-descriptions-item>
            <el-descriptions-item label="最新价">
              <span :class="getPriceClass(selectedTick.last_price, selectedTick.pre_close)">
                {{ selectedTick.last_price?.toFixed(2) || '-' }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="涨跌">
              <span :class="getChangeClass(selectedTick.change)">
                {{ selectedTick.change?.toFixed(2) || '-' }}
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="涨跌幅">
              <span :class="getChangeClass(selectedTick.change_percent)">
                {{ selectedTick.change_percent?.toFixed(2) || '-' }}%
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="开盘价">
              {{ selectedTick.open_price?.toFixed(2) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="最高价">
              {{ selectedTick.high_price?.toFixed(2) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="最低价">
              {{ selectedTick.low_price?.toFixed(2) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="昨收">
              {{ selectedTick.pre_close?.toFixed(2) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="成交量">
              {{ formatVolume(selectedTick.volume) }}
            </el-descriptions-item>
            <el-descriptions-item label="成交额">
              {{ formatMoney(selectedTick.turnover) }}
            </el-descriptions-item>
            <el-descriptions-item label="买一价">
              {{ selectedTick.bid_price_1?.toFixed(2) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="卖一价">
              {{ selectedTick.ask_price_1?.toFixed(2) || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="时间">
              {{ selectedTick.datetime || '-' }}
            </el-descriptions-item>
          </el-descriptions>
          <el-empty v-else description="请选择合约查看详情" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { formatVolume, formatMoney } from '@/utils/format'
import { useMarketStore } from '@/stores/market'
import CandleChart from '@/components/charts/CandleChart.vue'

const marketStore = useMarketStore()

const searchQuery = ref('')
const selectedSymbol = ref(null)
const interval = ref('1m')

const allTicks = computed(() => marketStore.getAllTicks())

const filteredTicks = computed(() => {
  if (!searchQuery.value) return allTicks.value
  return allTicks.value.filter(tick =>
    tick.vt_symbol.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})

const selectedTick = computed(() => {
  if (!selectedSymbol.value) return null
  return marketStore.getTickValue(selectedSymbol.value)
})

const isSubscribed = computed(() => {
  return selectedSymbol.value && marketStore.subscribedSymbols.has(selectedSymbol.value)
})

function getPriceClass(current, base) {
  if (!current || !base) return ''
  return current > base ? 'text-up' : current < base ? 'text-down' : ''
}

function getChangeClass(change) {
  if (!change) return ''
  return change > 0 ? 'text-up' : change < 0 ? 'text-down' : ''
}

function handleRowClick(row) {
  selectedSymbol.value = row.vt_symbol
}

function handleIntervalChange() {
  // K线周期变更时刷新数据
}

function toggleSubscribe() {
  if (!selectedSymbol.value) return

  if (isSubscribed.value) {
    marketStore.unsubscribeSymbol(selectedSymbol.value)
  } else {
    marketStore.subscribeSymbol(selectedSymbol.value)
  }
}

onMounted(async () => {
  // 加载已订阅列表
  await marketApi.getSubscribed()
})
</script>

<style scoped lang="scss">
.market-page {
  padding: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chart-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.el-table {
  :deep(.el-table__row) {
    cursor: pointer;

    &:hover {
      background-color: #f5f7fa;
    }
  }
}
</style>
