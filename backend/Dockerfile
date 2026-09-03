# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Nguồn apt mặc định (deb.debian.org qua HTTP) bị mạng VN chặn/rất chậm.
# Archive chính (debian) -> đổi sang mirror đặt tại VN (BizFly Cloud, không
# có debian-security nên suite đó chỉ ép sang HTTPS, giữ nguyên host).
# Cache mount giữ lại .deb/index giữa các lần build để không phải tải lại
# mỗi khi có commit mới (chỉ mất công tải lại khi danh sách package đổi).
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    sed -i \
        -e 's|URIs: http://deb.debian.org/debian$|URIs: https://mirror.bizflycloud.vn/debian|' \
        -e 's|URIs: http://deb.debian.org/debian-security$|URIs: https://deb.debian.org/debian-security|' \
        /etc/apt/sources.list.d/*.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev postgresql-client curl && \
    groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -d /app -s /sbin/nologin appuser

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy source với ownership appuser — không chạy root
COPY --chown=appuser:appuser . .

# Tạo thư mục log/tmp/backup với đúng permissions
RUN mkdir -p /app/logs /tmp/hrms_exports /backups/tmp && \
    chown -R appuser:appuser /app/logs /tmp/hrms_exports /backups

USER appuser

# Liveness probe — chỉ check app còn sống, không check dependencies
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
