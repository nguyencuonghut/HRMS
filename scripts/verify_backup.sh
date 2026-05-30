#!/usr/bin/env bash
# verify_backup.sh — verify PostgreSQL plain-SQL backup created by backup_db.sh
#
# Dùng:
#   bash scripts/verify_backup.sh /path/to/hrms_20260101_020000.sql.gz
#
# Environment variables (có thể override):
#   DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
#   VERIFY_DB_NAME_PREFIX  — prefix DB tạm (mặc định: hrms_verify)
#   REQUIRED_TABLES        — danh sách bảng bắt buộc, cách nhau bởi khoảng trắng

set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: bash scripts/verify_backup.sh /path/to/hrms_YYYYMMDD_HHMMSS.sql.gz" >&2
  exit 1
fi

BACKUP_FILE="$1"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5433}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-password}"
VERIFY_DB_NAME_PREFIX="${VERIFY_DB_NAME_PREFIX:-hrms_verify}"
REQUIRED_TABLES="${REQUIRED_TABLES:-employees departments users}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
VERIFY_DB_NAME="${VERIFY_DB_NAME_PREFIX}_${TIMESTAMP}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: Backup file not found: $BACKUP_FILE" >&2
  exit 1
fi

if [ ! -s "$BACKUP_FILE" ]; then
  echo "ERROR: Backup file is empty: $BACKUP_FILE" >&2
  exit 1
fi

PSQL_BASE=(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --no-password)
CREATEDB_BASE=(createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --no-password)
DROPDB_BASE=(dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --no-password)

cleanup() {
  PGPASSWORD="$DB_PASSWORD" "${DROPDB_BASE[@]}" --if-exists "$VERIFY_DB_NAME" >/dev/null 2>&1 || true
}

trap cleanup EXIT

echo "[$(date -Iseconds)] Verifying gzip integrity: $BACKUP_FILE"
gzip -t "$BACKUP_FILE"

echo "[$(date -Iseconds)] Creating temporary database: $VERIFY_DB_NAME"
PGPASSWORD="$DB_PASSWORD" "${CREATEDB_BASE[@]}" "$VERIFY_DB_NAME"

echo "[$(date -Iseconds)] Restoring backup into temporary database"
gunzip -c "$BACKUP_FILE" | PGPASSWORD="$DB_PASSWORD" "${PSQL_BASE[@]}" "$VERIFY_DB_NAME" >/dev/null

table_count="$(PGPASSWORD="$DB_PASSWORD" "${PSQL_BASE[@]}" "$VERIFY_DB_NAME" -Atqc "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")"
echo "[$(date -Iseconds)] Restored public tables: $table_count"
if [ "${table_count:-0}" -le 0 ]; then
  echo "ERROR: Restored database has no public tables" >&2
  exit 1
fi

for table_name in $REQUIRED_TABLES; do
  exists="$(PGPASSWORD="$DB_PASSWORD" "${PSQL_BASE[@]}" "$VERIFY_DB_NAME" -Atqc "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '${table_name}')")"
  if [ "$exists" != "t" ]; then
    echo "ERROR: Required table missing after restore: $table_name" >&2
    exit 1
  fi

  row_count="$(PGPASSWORD="$DB_PASSWORD" "${PSQL_BASE[@]}" "$VERIFY_DB_NAME" -Atqc "SELECT count(*) FROM ${table_name}")"
  echo "[$(date -Iseconds)] ${table_name}: ${row_count} row(s)"
done

echo "[$(date -Iseconds)] Backup verified OK ✓"
