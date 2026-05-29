#!/usr/bin/env bash
# backup_minio.sh — MinIO daily mirror backup (Plan 15.4)
#
# Dùng:
#   bash scripts/backup_minio.sh
#
# Yêu cầu: mc (MinIO Client) đã được cài và cấu hình aliases:
#   mc alias set local http://minio:9000 $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
#   mc alias set backup https://s3-backup.example.com $BACKUP_ACCESS_KEY $BACKUP_SECRET_KEY
#
# Environment variables:
#   SOURCE_ALIAS   — mc alias của MinIO nguồn (mặc định: local)
#   SOURCE_BUCKET  — bucket nguồn (mặc định: hrms-attachments-prod)
#   DEST_ALIAS     — mc alias của bucket backup (mặc định: backup)
#   DEST_BUCKET    — bucket đích (mặc định: hrms-backup)
#   RETENTION_DAYS — số ngày giữ snapshot (mặc định: 90)
#   LOG_DIR        — thư mục log (mặc định: /logs)

set -euo pipefail

SOURCE_ALIAS="${SOURCE_ALIAS:-local}"
SOURCE_BUCKET="${SOURCE_BUCKET:-hrms-attachments-prod}"
DEST_ALIAS="${DEST_ALIAS:-backup}"
DEST_BUCKET="${DEST_BUCKET:-hrms-backup}"
RETENTION_DAYS="${RETENTION_DAYS:-90}"
LOG_DIR="${LOG_DIR:-/logs}"
DATE=$(date +%Y%m%d)
LOG_FILE="$LOG_DIR/backup_minio_${DATE}.log"

mkdir -p "$LOG_DIR"

echo "[$(date -Iseconds)] Starting MinIO mirror: ${SOURCE_ALIAS}/${SOURCE_BUCKET} → ${DEST_ALIAS}/${DEST_BUCKET}/files-${DATE}/" | tee -a "$LOG_FILE"

# Check source exists
if ! mc ls "${SOURCE_ALIAS}/${SOURCE_BUCKET}/" &>/dev/null; then
    echo "[$(date -Iseconds)] ERROR: Source bucket not accessible: ${SOURCE_ALIAS}/${SOURCE_BUCKET}" | tee -a "$LOG_FILE" >&2
    exit 1
fi

# Mirror (incremental — chỉ copy files mới/thay đổi)
mc mirror \
    --overwrite \
    --preserve \
    "${SOURCE_ALIAS}/${SOURCE_BUCKET}" \
    "${DEST_ALIAS}/${DEST_BUCKET}/files-${DATE}/" \
    2>&1 | tee -a "$LOG_FILE"

OBJECT_COUNT=$(mc ls "${DEST_ALIAS}/${DEST_BUCKET}/files-${DATE}/" --recursive 2>/dev/null | wc -l)
echo "[$(date -Iseconds)] Mirror complete — $OBJECT_COUNT objects in snapshot files-${DATE}/" | tee -a "$LOG_FILE"

# Cleanup snapshots cũ hơn RETENTION_DAYS ngày
echo "[$(date -Iseconds)] Checking snapshots older than ${RETENTION_DAYS} days..." | tee -a "$LOG_FILE"

mc ls "${DEST_ALIAS}/${DEST_BUCKET}/" 2>/dev/null | awk '{print $NF}' | while read -r dir_raw; do
    dir="${dir_raw%/}"  # strip trailing slash
    # Chỉ xử lý snapshot folders theo format files-YYYYMMDD
    if [[ "$dir" =~ ^files-([0-9]{8})$ ]]; then
        dir_date="${BASH_REMATCH[1]}"
        # Tính tuổi snapshot (ngày)
        dir_epoch=$(date -d "$dir_date" +%s 2>/dev/null || date -j -f "%Y%m%d" "$dir_date" +%s 2>/dev/null || echo 0)
        now_epoch=$(date +%s)
        age_days=$(( (now_epoch - dir_epoch) / 86400 ))

        if [ "$age_days" -gt "$RETENTION_DAYS" ]; then
            echo "[$(date -Iseconds)] Removing old snapshot: ${dir} (${age_days} days old)" | tee -a "$LOG_FILE"
            mc rm --recursive --force "${DEST_ALIAS}/${DEST_BUCKET}/${dir}/" 2>&1 | tee -a "$LOG_FILE"
        fi
    fi
done

echo "[$(date -Iseconds)] Backup MinIO complete ✓" | tee -a "$LOG_FILE"
