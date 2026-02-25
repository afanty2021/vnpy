<template>
  <div class="alert-list">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="活动告警" name="active">
        <AlertListItem
          v-for="alert in activeAlerts"
          :key="alert.id"
          :alert="alert"
          @acknowledge="handleAcknowledge"
        />
        <el-empty
          v-if="activeAlerts.length === 0"
          description="暂无活动告警"
          :image-size="80"
        />
      </el-tab-pane>

      <el-tab-pane label="严重" name="critical">
        <AlertListItem
          v-for="alert in criticalAlerts"
          :key="alert.id"
          :alert="alert"
          @acknowledge="handleAcknowledge"
        />
        <el-empty
          v-if="criticalAlerts.length === 0"
          description="暂无严重告警"
          :image-size="80"
        />
      </el-tab-pane>

      <el-tab-pane label="警告" name="warning">
        <AlertListItem
          v-for="alert in warningAlerts"
          :key="alert.id"
          :alert="alert"
          @acknowledge="handleAcknowledge"
        />
        <el-empty
          v-if="warningAlerts.length === 0"
          description="暂无警告告警"
          :image-size="80"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useAlertStore } from '@/stores/alert'
import AlertListItem from './AlertListItem.vue'

const alertStore = useAlertStore()
const activeTab = ref('active')

const activeAlerts = computed(() => alertStore.activeAlerts)
const criticalAlerts = computed(() => alertStore.criticalAlerts)
const warningAlerts = computed(() => alertStore.warningAlerts)

async function handleAcknowledge(alertId, comment) {
  const success = await alertStore.acknowledgeAlert(alertId, comment)
  if (success) {
    ElMessage.success('告警已确认')
  }
}
</script>

<style scoped lang="scss">
.alert-list {
  height: 100%;
}
</style>
