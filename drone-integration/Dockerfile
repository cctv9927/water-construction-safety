# ============================================================
# Drone Integration Dockerfile - 无人机集成模块
# ============================================================
FROM node:18-alpine AS builder

WORKDIR /app

# 复制 package 文件
COPY package.json package-lock.json* ./

# 安装依赖（使用 lockfile 保证构建可重现）
RUN npm ci --only=production=false

# 复制源码
COPY tsconfig.json ./
COPY src/ ./src/

# 构建 TypeScript
RUN npm run build

# ───────────────────────────────────────────────
# 运行时镜像
# ───────────────────────────────────────────────
FROM node:18-alpine

# 防止 Node.js输出缓冲
ENV NODE_ENV=production
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 安装运行时依赖（轻量）
RUN apk add --no-cache wget

# 从构建阶段复制编译产物
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package.json ./

# 暴露端口（容器内）
EXPOSE 8090

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:8090/health || exit 1

# 启动命令
CMD ["npm", "start"]
