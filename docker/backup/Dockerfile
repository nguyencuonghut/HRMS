FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      bash \
      ca-certificates \
      curl \
      gcc \
      libpq-dev \
      postgresql-client \
      procps && \
    rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

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
