#!/usr/bin/env bash
# garage_bootstrap.sh — tạo bucket và khóa truy cập cho Garage (kế hoạch 15.7, Slice 2). Chạy lại an toàn.
#
# Dùng (dev, từ thư mục gốc repo):
#   docker compose up -d garage
#   bash scripts/garage_bootstrap.sh >> .env
#
# stdout CHỈ chứa các dòng KEY=VALUE của khóa vừa được TẠO MỚI (đây là bí mật, hiện đúng một lần); mọi thông báo
# ra stderr. Chạy lại khi bucket và khóa đã có: không tạo thêm gì và không in gì ra stdout. Nếu mất khóa:
#   docker compose exec garage /garage key info hrms-app --show-secret
#
# Việc script làm (đều theo kết quả Slice 1):
#   - bucket do CLI tạo (alias toàn cục); bucket tạo qua S3 chỉ có alias cục bộ của khóa tạo ra nó
#   - hrms-app    đọc/ghi/owner trên MINIO_BUCKET                 -> MINIO_ACCESS_KEY, MINIO_SECRET_KEY
#   - hrms-backup đọc/ghi/owner trên BACKUP_STORAGE_BUCKET         -> BACKUP_STORAGE_ACCESS_KEY, BACKUP_STORAGE_SECRET_KEY
#   - CẢ HAI khóa có quyền tạo bucket, vì mã ứng dụng gọi make_bucket ở hai nơi bằng hai khóa khác nhau:
#       backup_runner_service.py  tạo bucket đích sao lưu            (khóa hrms-backup)
#       restore_runner_service.py tạo bucket đích khi khôi phục kho tệp sang đích mới, bằng khóa ỨNG DỤNG (hrms-app)
#     (đã kiểm ở Slice 2: thiếu quyền này thì khôi phục kho tệp bị AccessDenied). Bucket tạo qua S3 chỉ có alias cục bộ
#     của khóa tạo ra nó.
#
# Biến môi trường (mặc định dùng cho dev):
#   COMPOSE_FILE          docker-compose.yml        (production LAN: docker-compose.lan.yml)
#   GARAGE_SERVICE        garage
#   GARAGE_CONTAINER      (trống)                    đặt tên container nếu Garage chạy bằng `docker run` (CI); khi đặt thì bỏ qua COMPOSE_FILE
#   MINIO_BUCKET          hrms-attachments-dev      (production: hrms-attachments-prod)
#   BACKUP_STORAGE_BUCKET hrms-backup
#   APP_KEY_NAME          hrms-app
#   BACKUP_KEY_NAME       hrms-backup
#   WAIT_SECONDS          60                        thời gian tối đa chờ Garage sẵn sàng
#
# Script nhắm vào project compose mặc định của thư mục (và `.env` trong thư mục). Để nhắm project hoặc file env khác (ví dụ khi thử
# song song với dev), đặt COMPOSE_PROJECT_NAME và COMPOSE_ENV_FILES; nếu không, nó sẽ tác động vào Garage của project `hrms`.

set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
GARAGE_SERVICE="${GARAGE_SERVICE:-garage}"
APP_BUCKET="${MINIO_BUCKET:-hrms-attachments-dev}"
BACKUP_BUCKET="${BACKUP_STORAGE_BUCKET:-hrms-backup}"
APP_KEY="${APP_KEY_NAME:-hrms-app}"
BACKUP_KEY="${BACKUP_KEY_NAME:-hrms-backup}"
WAIT_SECONDS="${WAIT_SECONDS:-60}"

# Mặc định gọi qua docker compose. Đặt GARAGE_CONTAINER=<tên container> khi Garage được chạy bằng `docker run`
# (CI: service container khởi động trước checkout nên không gắn được garage.toml từ repo), khi đó dùng `docker exec`.
if [ -n "${GARAGE_CONTAINER:-}" ]; then
  garage() { docker exec -i "$GARAGE_CONTAINER" /garage "$@"; }
else
  garage() { docker compose -f "$COMPOSE_FILE" exec -T "$GARAGE_SERVICE" /garage "$@"; }
fi
log() { echo "[garage_bootstrap] $*" >&2; }
die() { log "LỖI: $*"; exit 1; }

# Che mọi chuỗi hex dài 64 ký tự (dạng secret) trước khi in lỗi ra stderr.
mask() { sed -E 's/[0-9a-f]{64}/<đã ẩn>/g'; }
extract_key_id() { grep -oE 'GK[0-9a-f]{24,}' | head -1 || true; }
extract_secret() { grep -oE '(^|[^0-9a-f])[0-9a-f]{64}([^0-9a-f]|$)' | grep -oE '[0-9a-f]{64}' | head -1 || true; }

# Chạy một lệnh garage, ẩn đầu ra khi thành công, in đầu ra (đã che) ra stderr khi thất bại.
quiet() {
  local out
  if ! out="$(garage "$@" 2>&1)"; then
    printf '%s\n' "$out" | mask >&2
    die "lệnh 'garage $*' thất bại"
  fi
}

wait_until_ready() {
  local waited=0
  until garage health -q >/dev/null 2>&1; do
    [ "$waited" -lt "$WAIT_SECONDS" ] || die "Garage chưa sẵn sàng sau ${WAIT_SECONDS}s (service '$GARAGE_SERVICE', file '$COMPOSE_FILE'). Đã chạy 'docker compose up -d garage' chưa?"
    sleep 2
    waited=$((waited + 2))
  done
}

ensure_bucket() { # tên
  if garage bucket info "$1" >/dev/null 2>&1; then
    log "bucket $1: đã có"
  else
    quiet bucket create "$1"
    log "bucket $1: đã tạo"
  fi
}

# In ra stdout hai dòng <PREFIX>_ACCESS_KEY và <PREFIX>_SECRET_KEY, chỉ khi khóa được tạo mới.
ensure_key() { # tên_khóa tiền_tố_biến
  local name="$1" prefix="$2" out id secret
  if garage key info "$name" >/dev/null 2>&1; then
    log "khóa $name: đã có (không in lại secret)"
    return
  fi
  if ! out="$(garage key create "$name" 2>&1)"; then
    printf '%s\n' "$out" | mask >&2
    die "không tạo được khóa $name"
  fi
  id="$(extract_key_id <<<"$out")"
  secret="$(extract_secret <<<"$out")"
  if [ -z "$id" ] || [ "${#secret}" -ne 64 ]; then
    die "khóa $name đã được tạo nhưng không đọc được ID/secret từ đầu ra. Xóa khóa rồi chạy lại: docker compose -f $COMPOSE_FILE exec $GARAGE_SERVICE /garage key delete --yes $name"
  fi
  printf '%s_ACCESS_KEY=%s\n%s_SECRET_KEY=%s\n' "$prefix" "$id" "$prefix" "$secret"
  log "khóa $name: đã tạo (ID $id); secret in ra stdout đúng một lần"
}

wait_until_ready
log "Garage sẵn sàng"

ensure_bucket "$APP_BUCKET"
ensure_bucket "$BACKUP_BUCKET"
ensure_key "$APP_KEY" MINIO
ensure_key "$BACKUP_KEY" BACKUP_STORAGE

# Các lệnh cấp quyền đều idempotent.
quiet bucket allow --read --write --owner "$APP_BUCKET" --key "$APP_KEY"
quiet bucket allow --read --write --owner "$BACKUP_BUCKET" --key "$BACKUP_KEY"
quiet key allow --create-bucket "$APP_KEY"
quiet key allow --create-bucket "$BACKUP_KEY"
log "quyền: $APP_KEY -> $APP_BUCKET (RWO) + tạo bucket; $BACKUP_KEY -> $BACKUP_BUCKET (RWO) + tạo bucket"
