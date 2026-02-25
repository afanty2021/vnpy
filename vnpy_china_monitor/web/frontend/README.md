# VeighNa Web Monitor - 前端

基于Vue.js 3 + Vite构建的VeighNa量化交易监控系统前端。

## 技术栈

- **框架**: Vue.js 3.4+ (Composition API)
- **构建工具**: Vite 5.x
- **UI组件库**: Element Plus 2.6+
- **图表库**: ECharts 5.5+
- **状态管理**: Pinia 2.x
- **路由**: Vue Router 4.x
- **HTTP客户端**: Axios 1.x
- **WebSocket**: 原生WebSocket API
- **CSS预处理**: Sass

## 项目结构

```
frontend/
├── public/                 # 静态资源
├── src/
│   ├── api/               # API接口
│   │   ├── request.js     # Axios配置
│   │   ├── auth.js        # 认证API
│   │   ├── market.js      # 行情API
│   │   ├── trade.js       # 交易API
│   │   ├── strategy.js    # 策略API
│   │   └── alert.js       # 告警API
│   ├── assets/            # 资源文件
│   │   └── styles/        # 样式文件
│   │       └── main.scss  # 全局样式
│   ├── components/        # 通用组件
│   │   ├── Layout.vue     # 布局组件
│   │   ├── AlertList.vue  # 告警列表
│   │   ├── charts/        # 图表组件
│   │   └── dashboard/     # 仪表盘组件
│   ├── router/            # 路由配置
│   │   └── index.js
│   ├── stores/            # Pinia状态管理
│   │   ├── auth.js        # 认证状态
│   │   ├── market.js      # 行情状态
│   │   ├── trade.js       # 交易状态
│   │   ├── strategy.js    # 策略状态
│   │   └── alert.js       # 告警状态
│   ├── utils/             # 工具函数
│   │   ├── format.js      # 格式化函数
│   │   └── websocket.js   # WebSocket客户端
│   ├── views/             # 页面组件
│   │   ├── Login.vue      # 登录页
│   │   ├── Dashboard.vue  # 仪表盘
│   │   ├── Market.vue     # 行情页
│   │   ├── Trade.vue      # 交易页
│   │   ├── Position.vue   # 持仓页
│   │   ├── Strategy.vue   # 策略页
│   │   ├── Alerts.vue     # 告警页
│   │   └── Settings.vue   # 设置页
│   ├── App.vue            # 根组件
│   └── main.js            # 入口文件
├── index.html             # HTML模板
├── vite.config.js         # Vite配置
├── package.json           # 项目配置
└── README.md              # 项目文档

## 开发指南

### 环境要求

- Node.js >= 16.x
- npm >= 8.x 或 pnpm >= 7.x

### 安装依赖

```bash
cd frontend
npm install
# 或
pnpm install
```

### 开发模式

```bash
npm run dev
# 或
pnpm dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
# 或
pnpm build
```

### 预览生产构建

```bash
npm run preview
# 或
pnpm preview
```

## 代码规范

### 命名规范

- 组件文件: PascalCase (如 `Dashboard.vue`)
- 工具文件: camelCase (如 `format.js`)
- 状态文件: camelCase (如 `auth.js`)

### 组件开发

使用Composition API编写组件：

```vue
<template>
  <div class="my-component">
    {{ message }}
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

// 响应式数据
const message = ref('Hello')
const count = ref(0)

// 计算属性
const doubleCount = computed(() => count.value * 2)

// 方法
function increment() {
  count.value++
}

// 生命周期
onMounted(() => {
  console.log('Component mounted')
})
</script>

<style scoped lang="scss">
.my-component {
  font-size: 14px;
}
</style>
```

### 状态管理

使用Pinia进行状态管理：

```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useMyStore = defineStore('my', () => {
  // state
  const data = ref([])

  // getters
  const filteredData = computed(() => {
    return data.value.filter(...)
  })

  // actions
  async function fetchData() {
    // ...
  }

  return {
    data,
    filteredData,
    fetchData
  }
})
```

### API调用

使用统一的API模块：

```javascript
import { marketApi } from '@/api/market'

// 获取行情
const tick = await marketApi.getTick('000001.SZSE')

// 订阅行情
await marketApi.subscribe('000001.SZSE')
```

## WebSocket连接

WebSocket自动在应用启动时连接，需要确保后端服务已启动。

```javascript
import { useWebSocket } from '@/utils/websocket'

// 初始化WebSocket（在Layout组件中自动完成）
const wsClient = useWebSocket(clientId)

// 订阅事件
wsClient.on('market_tick', (data) => {
  console.log('收到行情:', data)
})
```

## 部署

### Docker部署

```dockerfile
# 构建阶段
FROM node:16-alpine as build-stage
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# 生产阶段
FROM nginx:alpine as production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 环境变量

创建 `.env.production` 文件：

```
VITE_API_BASE_URL=/api
VITE_WS_HOST=your-production-host:8000
```

## 浏览器支持

- Chrome >= 87
- Firefox >= 78
- Safari >= 14
- Edge >= 88

## 许可证

MIT
