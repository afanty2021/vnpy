<template>
  <el-card class="alert-item" :class="`alert-${alert.severity}`">
    <div class="alert-header">
      <div class="alert-title">
        <el-icon>
          <Warning v-if="alert.severity === 'critical'" />
          <WarningFilled v-else-if="alert.severity === 'warning'" />
          <InfoFilled v-else />
        </el-icon>
        <span>{{ alert.title }}</span>
      </div>
      <el-tag :type="severityType" size="small">
        {{ severityText }}
      </el-tag>
    </div>

    <div class="alert-message">
      {{ alert.message }}
    </div>

    <div class="alert-meta">
      <span class="alert-time">
        {{ formatTime(alert.timestamp) }}
      </span>
      <span class="alert-source">
        {{ alert.source }}
      </span>
    </div>

    <div v-if="!alert.acknowledged" class="alert-actions">
      <el-input
        v-model="comment"
        placeholder="添加备注（可选）"
        size="small"
        class="comment-input"
      />
      <el-button
        type="primary"
        size="small"
        @click="handleAcknowledge"
      >
        确认
      </el-button>
    </div>

    <div v-else class="alert-acknowledged">
      <el-icon color="#67c23a"><Select /></el-icon>
      <span>已确认 by {{ alert.acknowledged_by }}</span>
      <span class="ack-time">{{ formatTime(alert.acknowledged_at) }}</span>
    </div>
  </el-card>
</template>

<script setup>
import { ref, computed } from 'vue'
import { formatDateTime } from '@/utils/format'
import {
  Warning,
  WarningFilled,
  InfoFilled,
  Select
} from '@element-plus/icons-vue'

const props = defineProps({
  alert: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['acknowledge'])

const comment = ref('')

const severityType = computed(() => {
  const typeMap = {
    critical: 'danger',
    warning: 'warning',
    info: 'info'
  }
  return typeMap[props.alert.severity] || 'info'
})

const severityText = computed(() => {
  const textMap = {
    critical: '严重',
    warning: '警告',
    info: '信息'
  }
  return textMap[props.alert.severity] || '未知'
})

function formatTime(timestamp) {
  return formatDateTime(timestamp, 'MM-DD HH:mm')
}

function handleAcknowledge() {
  emit('acknowledge', props.alert.id, comment.value)
  comment.value = ''
}
</script>

<style scoped lang="scss">
.alert-item {
  margin-bottom: 12px;

  &:last-child {
    margin-bottom: 0;
  }

  &.alert-critical {
    border-left: 4px solid #f56c6c;
  }

  &.alert-warning {
    border-left: 4px solid #e6a23c;
  }

  &.alert-info {
    border-left: 4px solid #409eff;
  }

  :deep(.el-card__body) {
    padding: 12px;
  }
}

.alert-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.alert-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 14px;
}

.alert-message {
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 8px;
}

.alert-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
}

.alert-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;

  .comment-input {
    flex: 1;
  }
}

.alert-acknowledged {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 8px;
  font-size: 12px;
  color: #67c23a;

  .ack-time {
    margin-left: auto;
    color: #909399;
  }
}
</style>
