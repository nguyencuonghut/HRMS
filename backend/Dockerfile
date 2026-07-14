FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Cài system deps + tạo non-root user trong một layer để tối ưu image size
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev postgresql-client curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r appuser && \
    useradd -r -g appuser -u 1000 -d /app -s /sbin/nologin appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

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
