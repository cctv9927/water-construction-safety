# EasyDarwin 流媒体服务 Dockerfile
# 注意：这是简化版本，仅用于本地开发测试
# 生产环境请使用官方 EasyDarwin: https://github.com/EasyDarwin/EasyDarwin

FROM alpine:latest

RUN apk add --no-cache socat

# 默认配置
COPY config.toml /app/config.toml

EXPOSE 10000 1935 8080

# 使用 socat 模拟基本服务响应
CMD ["socat", "- TCP-LISTEN:8080,fork,reuseaddr"]
