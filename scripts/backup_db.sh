#!/usr/bin/env bash
# backup_db.sh — PostgreSQL daily backup (Plan 15.4)
#
# Dùng:
#   bash scripts/backup_db.sh
#
# Hoặc qua Docker:
#   docker exec hrms-db-1 bash /scripts/backup_db.sh
#
# Environment variables (có thể override qua .env):
#   DB_HOST, DB_PORT, DB_USER, DB_NAME, DB_PASSWORD
#   BACKUP_DIR  — thư mục lưu backup (mặc định: /backups/postgres)
#   RETENTION_DAYS — số ngày giữ backup (mặc định: 90)

set -euo pipefail

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-hrms}"
DB_PASSWORD="${DB_PASSWORD:-password}"
BACKUP_DIR="${BACKUP_DIR:-/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-90}"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="hrms_${DATE}.sql.gz"
BACKUP_NOTIFY_COMMAND="${BACKUP_NOTIFY_COMMAND:-}"
STARTED_AT="$(date -Iseconds)"
BACKUP_NOTIFY_SENT=0

mkdir -p "$BACKUP_DIR"

notify_backup_status() {
    local status="$1"
    local summary="$2"
    local details="$3"
    if [ -z "$BACKUP_NOTIFY_COMMAND" ] || [ "$BACKUP_NOTIFY_SENT" -eq 1 ]; then
        return 0
    fi
    BACKUP_NOTIFY_SENT=1
    BACKUP_NOTIFY_JOB_NAME="PostgreSQL backup" \
    BACKUP_NOTIFY_STATUS="$status" \
    BACKUP_NOTIFY_SUMMARY="$summary" \
    BACKUP_NOTIFY_DETAILS="$details" \
    BACKUP_NOTIFY_STARTED_AT="$STARTED_AT" \
    BACKUP_NOTIFY_FINISHED_AT="$(date -Iseconds)" \
    BACKUP_NOTIFY_HOSTNAME="$(hostname)" \
    sh -lc "$BACKUP_NOTIFY_COMMAND" || echo "[$(date -Iseconds)] WARNING: backup notification command failed" >&2
}

on_error() {
    local exit_code=$?
    set +e
    notify_backup_status "failed" "Backup PostgreSQL thất bại" "exit_code=${exit_code}; file=${BACKUP_DIR}/${FILENAME}"
    exit "$exit_code"
}

trap on_error ERR

echo "[$(date -Iseconds)] Starting backup: $FILENAME"

# Dump + compress (gzip level 9 = best compression)
PGPASSWORD="$DB_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -p "$DB_PORT" \
    -U "$DB_USER" \
    --no-password \
    "$DB_NAME" \
    | gzip -9 > "$BACKUP_DIR/$FILENAME"

SIZE=$(du -sh "$BACKUP_DIR/$FILENAME" | cut -f1)
echo "[$(date -Iseconds)] Backup created: $BACKUP_DIR/$FILENAME ($SIZE)"

# Verify file is non-empty
if [ ! -s "$BACKUP_DIR/$FILENAME" ]; then
    echo "[$(date -Iseconds)] ERROR: Backup file is empty!" >&2
    exit 1
fi

# Upload to MinIO backup bucket (nếu mc đã được cấu hình)
if command -v mc &>/dev/null && mc ls backup/ &>/dev/null 2>&1; then
    mc cp "$BACKUP_DIR/$FILENAME" "backup/hrms-db-backups/$FILENAME"
    echo "[$(date -Iseconds)] Uploaded to backup bucket: backup/hrms-db-backups/$FILENAME"
else
    echo "[$(date -Iseconds)] mc not configured — skipping remote upload"
fi

# Cleanup: xóa backup cũ hơn RETENTION_DAYS ngày
DELETED=$(find "$BACKUP_DIR" -name "hrms_*.sql.gz" -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
echo "[$(date -Iseconds)] Cleaned up $DELETED backup(s) older than ${RETENTION_DAYS} days"

echo "[$(date -Iseconds)] Backup complete ✓"
notify_backup_status "success" "Backup PostgreSQL hoàn tất" "file=${BACKUP_DIR}/${FILENAME}; size=${SIZE}; retention_days=${RETENTION_DAYS}"
