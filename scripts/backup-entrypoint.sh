#!/usr/bin/env bash

set -euo pipefail

DB_BACKUP_CRON="${DB_BACKUP_CRON:-0 2 * * *}"
MINIO_BACKUP_CRON="${MINIO_BACKUP_CRON:-0 3 * * *}"
BACKUP_NOTIFY_COMMAND="${BACKUP_NOTIFY_COMMAND:-python -m app.scripts.send_backup_notification}"
BACKUP_CRON_FILE="/etc/supercronic/backup.crontab"

mkdir -p /backups/postgres /logs /etc/supercronic

normalize_endpoint() {
    local endpoint="$1"
    local secure="${2:-false}"
    if [[ "$endpoint" == http://* || "$endpoint" == https://* ]]; then
        printf '%s' "$endpoint"
        return 0
    fi
    if [[ "$secure" == "true" ]]; then
        printf 'https://%s' "$endpoint"
    else
        printf 'http://%s' "$endpoint"
    fi
}

configure_mc_alias() {
    local alias_name="$1"
    local endpoint="$2"
    local access_key="$3"
    local secret_key="$4"
    local secure="$5"

    if [[ -z "$endpoint" || -z "$access_key" || -z "$secret_key" ]]; then
        echo "Missing storage config for mc alias '${alias_name}'" >&2
        return 1
    fi

    mc alias set \
        "$alias_name" \
        "$(normalize_endpoint "$endpoint" "$secure")" \
        "$access_key" \
        "$secret_key"
}

configure_mc_alias \
    "${SOURCE_ALIAS:-local}" \
    "${SOURCE_STORAGE_ENDPOINT:-${MINIO_ENDPOINT:-}}" \
    "${SOURCE_STORAGE_ACCESS_KEY:-${MINIO_ACCESS_KEY:-}}" \
    "${SOURCE_STORAGE_SECRET_KEY:-${MINIO_SECRET_KEY:-}}" \
    "${SOURCE_STORAGE_SECURE:-${MINIO_SECURE:-false}}"

configure_mc_alias \
    "${DEST_ALIAS:-backup}" \
    "${BACKUP_STORAGE_ENDPOINT:-}" \
    "${BACKUP_STORAGE_ACCESS_KEY:-}" \
    "${BACKUP_STORAGE_SECRET_KEY:-}" \
    "${BACKUP_STORAGE_SECURE:-true}"

cat > "$BACKUP_CRON_FILE" <<EOF
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

$DB_BACKUP_CRON bash /scripts/backup_db.sh >> /logs/backup_db.log 2>&1
$MINIO_BACKUP_CRON bash /scripts/backup_minio.sh >> /logs/backup_minio.log 2>&1
EOF

echo "Starting backup scheduler with crontab:"
cat "$BACKUP_CRON_FILE"

exec /usr/local/bin/supercronic "$BACKUP_CRON_FILE"
