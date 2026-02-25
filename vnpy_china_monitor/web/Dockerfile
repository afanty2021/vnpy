# VeighNa Web Monitor - Dockerfile
# 多阶段构建，用于生产部署

# 阶段1: 构建前端
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# 复制前端项目文件
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# 阶段2: Python运行环境
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制requirements文件
COPY web/requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY web/ ./

# 从前端构建阶段复制构建产物
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# 创建非root用户
RUN useradd -m -u 1000 vnpy && \
    chown -R vnpy:vnpy /app

USER vnpy

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# 启动命令
CMD ["uvicorn", "vnpy_china_monitor.web.server:app", "--host", "0.0.0.0", "--port", "8000"]
