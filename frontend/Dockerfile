# syntax=docker/dockerfile:1
# ── Build stage ───────────────────────────────────────────────────────────────
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci
COPY . .
RUN npm run build

# ── Serve stage ───────────────────────────────────────────────────────────────
FROM nginx:alpine

# nginx:alpine chạy master process với root (cần bind port 80)
# và worker processes với user `nginx` — đây là pattern chuẩn
# Đảm bảo html files có permission đúng cho nginx user
COPY --from=builder --chown=nginx:nginx /app/dist /usr/share/nginx/html
COPY --chown=nginx:nginx nginx.conf /etc/nginx/conf.d/default.conf

# Cấu hình nginx chạy worker không cần root capabilities
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown nginx:nginx /var/run/nginx.pid

EXPOSE 80

# Dùng 127.0.0.1 thay vì localhost: wget (busybox) phân giải localhost ra ::1 trước,
# trong khi nginx chỉ `listen 80;` (IPv4) nên healthcheck luôn báo "Connection refused".
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/index.html || exit 1
