# ============================================================
# Gateway Dockerfile - 统一接入网关
# ============================================================
FROM python:3.11-slim

# 防止 Python 输出缓冲
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口（容器内）
EXPOSE 8001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# 启动命令
# 配置文件可通过 volume 挂载到 /app/config.yaml
CMD ["uvicorn", "gateway.main:app", "--host", "0.0.0.0", "--port", "8001"]
