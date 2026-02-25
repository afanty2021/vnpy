<template>
  <el-container class="layout-container">
    <el-aside width="200px" class="layout-aside">
      <div class="logo">
        <el-icon><Operation /></el-icon>
        <span>VeighNa</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        router
        class="layout-menu"
      >
        <el-menu-item
          v-for="route in menuRoutes"
          :key="route.path"
          :index="route.path"
        >
          <el-icon>
            <component :is="route.meta.icon" />
          </el-icon>
          <template #title>{{ route.meta.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-left">
          <el-button
            :icon="isCollapse ? Expand : Fold"
            @click="toggleCollapse"
            text
          />
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">
              首页
            </el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentRoute.meta.title">
              {{ currentRoute.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-right">
          <!-- WebSocket状态 -->
          <div class="ws-status" :class="{ connected: wsConnected }">
            <el-icon><Connection /></el-icon>
            <span>{{ wsConnected ? '已连接' : '未连接' }}</span>
          </div>

          <!-- 告警通知 -->
          <el-badge :value="alertCount" :hidden="alertCount === 0">
            <el-button :icon="Bell" text @click="showAlerts = true" />
          </el-badge>

          <!-- 用户菜单 -->
          <el-dropdown @command="handleUserCommand">
            <div class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ authStore.user?.username || 'User' }}</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人信息
                </el-dropdown-item>
                <el-dropdown-item command="settings">
                  <el-icon><Setting /></el-icon>
                  设置
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="layout-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <!-- 告警抽屉 -->
    <el-drawer
      v-model="showAlerts"
      title="活动告警"
      size="400px"
    >
      <AlertList />
    </el-drawer>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useAlertStore } from '@/stores/alert'
import { useWebSocket, disconnectWebSocket } from '@/utils/websocket'
import {
  Operation,
  Expand,
  Fold,
  Connection,
  Bell,
  UserFilled,
  User,
  Setting,
  SwitchButton
} from '@element-plus/icons-vue'
import AlertList from './AlertList.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const alertStore = useAlertStore()

const isCollapse = ref(false)
const wsConnected = ref(false)
const showAlerts = ref(false)

// 菜单路由
const menuRoutes = computed(() => {
  return router.getRoutes()
    .filter(r => r.meta?.title && r.path !== '/login')
    .sort((a, b) => (a.meta.order || 999) - (b.meta.order || 999))
})

const activeMenu = computed(() => route.path)
const currentRoute = computed(() => route)
const alertCount = computed(() => alertStore.activeAlerts.length)

function toggleCollapse() {
  isCollapse.value = !isCollapse.value
}

async function handleUserCommand(command) {
  switch (command) {
    case 'profile':
      // 跳转到个人信息页面
      break
    case 'settings':
      router.push('/settings')
      break
    case 'logout':
      await authStore.logout()
      disconnectWebSocket()
      router.push('/login')
      break
  }
}

onMounted(() => {
  // 初始化WebSocket
  const clientId = `web_${Date.now()}`
  const wsClient = useWebSocket(clientId)

  wsClient.on('open', () => {
    wsConnected.value = true
  })

  wsClient.on('close', () => {
    wsConnected.value = false
  })

  // 初始化告警WebSocket
  alertStore.initWebSocket(clientId)

  // 获取用户信息
  if (authStore.isLoggedIn) {
    authStore.getUserInfo()
  }

  // 加载告警
  alertStore.fetchAlerts({ active: true })
  alertStore.fetchStats()
})

onUnmounted(() => {
  disconnectWebSocket()
})
</script>

<style scoped lang="scss">
.layout-container {
  width: 100%;
  height: 100%;
}

.layout-aside {
  background-color: #304156;
  color: #fff;
  overflow-x: hidden;
  overflow-y: auto;

  .logo {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 60px;
    font-size: 20px;
    font-weight: bold;
    color: #fff;

    .el-icon {
      margin-right: 8px;
      font-size: 24px;
    }
  }

  .layout-menu {
    border: none;
    background-color: #304156;

    :deep(.el-menu-item) {
      color: #bfcbd9;

      &:hover {
        background-color: #263445;
      }

      &.is-active {
        color: #409eff;
        background-color: #263445;
      }
    }
  }
}

.layout-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  padding: 0 20px;

  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 20px;

    .ws-status {
      display: flex;
      align-items: center;
      gap: 4px;
      color: #f56c6c;

      &.connected {
        color: #67c23a;
      }
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;

      .username {
        font-size: 14px;
      }
    }
  }
}

.layout-main {
  background-color: #f0f2f5;
  overflow: auto;
}

// 过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
