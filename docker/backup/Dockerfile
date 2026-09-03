# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Nguồn apt mặc định (deb.debian.org qua HTTP) bị mạng VN chặn/rất chậm —
# xem giải thích chi tiết trong backend/Dockerfile.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    sed -i \
        -e 's|URIs: http://deb.debian.org/debian$|URIs: https://mirror.bizflycloud.vn/debian|' \
        -e 's|URIs: http://deb.debian.org/debian-security$|URIs: https://deb.debian.org/debian-security|' \
        /etc/apt/sources.list.d/*.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      gcc \
      libpq-dev \
      postgresql-client \
      procps

COPY backend/requirements.txt /app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/requirements.txt

COPY backend/app /app/app
COPY scripts/backup_db.sh /scripts/backup_db.sh
COPY scripts/backup_minio.sh /scripts/backup_minio.sh
COPY scripts/backup-entrypoint.sh /usr/local/bin/backup-entrypoint.sh

RUN chmod +x /scripts/backup_db.sh /scripts/backup_minio.sh /usr/local/bin/backup-entrypoint.sh && \
    curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc && \
    chmod +x /usr/local/bin/mc && \
    curl -fsSL https://github.com/aptible/supercronic/releases/download/v0.2.29/supercronic-linux-amd64 -o /usr/local/bin/supercronic && \
    chmod +x /usr/local/bin/supercronic && \
    mkdir -p /backups/postgres /logs /etc/supercronic

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD pgrep -f supercronic >/dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/backup-entrypoint.sh"]
