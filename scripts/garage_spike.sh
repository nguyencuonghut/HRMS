#!/usr/bin/env bash
# garage_spike.sh — Slice 1 của kế hoạch 15.7: kiểm tra Garage có tương thích với ứng dụng hay không.
#
# CHỈ CHẠY TRÊN MÁY DEV, không chạy trên production. Mọi thứ nằm trong một project compose tạm
# (mạng riêng, volume riêng) và được dọn sạch khi kết thúc. Khóa truy cập chỉ nằm trong biến shell,
# không được in ra hay ghi file; đầu ra của script không chứa bí mật nên có thể dán nguyên văn.
#
# Dùng (từ thư mục gốc repo):
#   bash scripts/garage_spike.sh 2>&1 | tee /tmp/garage_spike.out
#
# Biến tùy chọn:
#   GARAGE_IMAGE  image Garage cần thử   (mặc định: dxflrs/garage:v2.5.0)
#   PROBE_IMAGE   image có SDK S3        (mặc định: hrms-backend:latest, build từ docker-compose.yml)
#   KEEP=1        không dọn container/volume khi kết thúc (để xem thủ công; tự dọn bằng lệnh in ở cuối)
#
# Healthcheck dùng `garage health -q` (thoát 1 khi cụm không sẵn sàng). Đọc mã nguồn v2.5.0 cho thấy
# `garage status` chỉ thoát khác 0 khi RPC hỏng, nên không phản ánh sức khỏe; script vẫn ghi mã thoát của cả hai.
#
# Hai instance Garage được dựng:
#   garage          đúng cấu hình ở Phụ lục A (fsync bật, snapshot tự động 6h)
#   garage_nofsync  như trên nhưng fsync tắt (để so độ trễ, U10)
# Chu kỳ snapshot tối thiểu là 10 phút: giá trị nhỏ hơn (ví dụ "1min") làm Garage v2.5.0 không khởi động được
# (xem scripts/garage_spike_crash.sh và mục "Kết quả Slice 1" trong kế hoạch).

set -uo pipefail
cd "$(dirname "$0")/.."

GARAGE_IMAGE="${GARAGE_IMAGE:-dxflrs/garage:v2.5.0}"
PROBE_IMAGE="${PROBE_IMAGE:-hrms-backend:latest}"
PROBE_SRC="$PWD/backend/app/scripts/s3_conformance_probe.py"
KEY_NAME="spike-key"
APP_BUCKET="spike-app"

rand_hex() { od -An -N"$1" -tx1 /dev/urandom | tr -d ' \n'; }

PROJECT="g157spike$(rand_hex 4)"
WORK="$(mktemp -d)"
export GARAGE_IMAGE PROBE_IMAGE
GARAGE_RPC_SECRET="$(rand_hex 32)"
GARAGE_ADMIN_TOKEN="$(rand_hex 32)"
export GARAGE_RPC_SECRET GARAGE_ADMIN_TOKEN

SUMMARY=()

dc() { docker compose -p "$PROJECT" -f "$WORK/compose.yml" "$@"; }
g() { local svc="$1"; shift; dc exec -T "$svc" /garage "$@"; }

cleanup() {
  if [ "${KEEP:-0}" = "1" ]; then
    echo
    echo "KEEP=1: giữ lại. Dọn bằng: docker compose -p $PROJECT -f $WORK/compose.yml down -v && rm -rf $WORK"
    return
  fi
  dc down -v --remove-orphans >/dev/null 2>&1
  rm -rf "$WORK"
}
trap cleanup EXIT

# Che đúng các bí mật đã biết (secret của khóa, rpc_secret, admin_token) và mọi dòng "Secret key:".
# Không che theo độ dài 64 hex vì digest image và ID bucket cũng dài như vậy và cần giữ lại.
mask_secrets() {
  local args=(-E -e 's/(Secret key:[[:space:]]*)[0-9a-f]{64}/\1<đã ẩn>/') v
  for v in "$GARAGE_RPC_SECRET" "$GARAGE_ADMIN_TOKEN" "${SECRET:-}"; do
    [ -n "$v" ] && args+=(-e "s/$v/<đã ẩn>/g")
  done
  sed "${args[@]}"
}
extract_key_id() { grep -oE 'GK[0-9a-f]{24,}' | head -1; }
extract_secret() { grep -oE '(^|[^0-9a-f])[0-9a-f]{64}([^0-9a-f]|$)' | grep -oE '[0-9a-f]{64}' | head -1; }

# Chạy một lệnh, in đầu ra và mã thoát thật; không dừng script khi lệnh lỗi (mã lỗi cũng là dữ liệu).
step() {
  local label="$1" rc
  shift
  printf '\n=== %s\n' "$label"
  "$@" 2>&1 | mask_secrets
  rc=${PIPESTATUS[0]}
  printf '[exit=%s]\n' "$rc"
}

write_compose() {
  # Cấu hình Phụ lục A; rpc_secret và admin_token lấy từ biến môi trường (xác minh luôn điều đó, U17).
  write_toml() { # file fsync
    cat >"$1" <<TOML
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"

db_engine = "sqlite"
metadata_fsync = $2
data_fsync = $2
metadata_auto_snapshot_interval = "6h"

replication_factor = 1

rpc_bind_addr = "0.0.0.0:3901"
rpc_public_addr = "127.0.0.1:3901"

[s3_api]
s3_region = "garage"
api_bind_addr = "0.0.0.0:3900"

[admin]
api_bind_addr = "0.0.0.0:3903"
TOML
  }
  write_toml "$WORK/garage.toml" true
  write_toml "$WORK/garage_nofsync.toml" false

  cat >"$WORK/compose.yml" <<'YAML'
services:
  garage:
    image: ${GARAGE_IMAGE}
    command: ["/garage", "server", "--single-node"]
    environment:
      GARAGE_RPC_SECRET: ${GARAGE_RPC_SECRET}
      GARAGE_ADMIN_TOKEN: ${GARAGE_ADMIN_TOKEN}
    volumes:
      - ./garage.toml:/etc/garage.toml:ro
      - meta:/var/lib/garage/meta
      - data:/var/lib/garage/data
    healthcheck:
      test: ["CMD", "/garage", "health", "-q"]
      interval: 5s
      timeout: 5s
      retries: 12
  garage_nofsync:
    image: ${GARAGE_IMAGE}
    command: ["/garage", "server", "--single-node"]
    environment:
      GARAGE_RPC_SECRET: ${GARAGE_RPC_SECRET}
      GARAGE_ADMIN_TOKEN: ${GARAGE_ADMIN_TOKEN}
    volumes:
      - ./garage_nofsync.toml:/etc/garage.toml:ro
      - meta_nofsync:/var/lib/garage/meta
      - data_nofsync:/var/lib/garage/data
    healthcheck:
      test: ["CMD", "/garage", "health", "-q"]
      interval: 5s
      timeout: 5s
      retries: 12
  gate:
    image: ${PROBE_IMAGE}
    entrypoint: ["python", "-c", "print('gate đã chạy sau khi garage healthy')"]
    depends_on:
      garage:
        condition: service_healthy
    restart: "no"
volumes:
  meta:
  data:
  meta_nofsync:
  data_nofsync:
YAML
}

# Chạy probe trên mạng của project, khóa truyền qua biến môi trường (không nằm trên dòng lệnh).
run_probe() { # nhãn, dịch vụ, tham số thêm...
  local label="$1" svc="$2" out rc
  shift 2
  printf '\n--- probe %s/%s\n' "$svc" "$label"
  out="$(S3_PROBE_ACCESS_KEY="$ACCESS" S3_PROBE_SECRET_KEY="$SECRET" docker run --rm --network "${PROJECT}_default" \
    -e S3_PROBE_ACCESS_KEY -e S3_PROBE_SECRET_KEY -v "$PROBE_SRC:/probe.py:ro" --entrypoint python "$PROBE_IMAGE" \
    /probe.py --endpoint "$svc:3900" "$@" 2>&1)"
  rc=$?
  mask_secrets <<<"$out"
  printf '[exit=%s]\n' "$rc"
  SUMMARY+=("$svc | $label | exit=$rc | $(grep -E '^KẾT QUẢ' <<<"$out")")
  # Nếu lỗi có dấu hiệu liên quan region (U5), thử lại với --region garage để biết đó có phải cách khắc phục.
  if [ "$rc" -ne 0 ] && grep -qiE 'AuthorizationHeaderMalformed|region' <<<"$out"; then
    printf '\n--- probe %s/%s (thử lại với --region garage)\n' "$svc" "$label"
    out="$(S3_PROBE_ACCESS_KEY="$ACCESS" S3_PROBE_SECRET_KEY="$SECRET" docker run --rm --network "${PROJECT}_default" \
      -e S3_PROBE_ACCESS_KEY -e S3_PROBE_SECRET_KEY -v "$PROBE_SRC:/probe.py:ro" --entrypoint python "$PROBE_IMAGE" \
      /probe.py --endpoint "$svc:3900" --region garage "$@" 2>&1)"
    rc=$?
    mask_secrets <<<"$out"
    printf '[exit=%s]\n' "$rc"
    SUMMARY+=("$svc | $label + --region garage | exit=$rc | $(grep -E '^KẾT QUẢ' <<<"$out")")
  fi
}

running() { [ "$(docker inspect --format '{{.State.Running}}' "$(dc ps -a -q "$1")" 2>/dev/null)" = "true" ]; }

state_of() { docker inspect --format 'state={{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} error={{.State.Error}} started={{.State.StartedAt}} finished={{.State.FinishedAt}}' "$(dc ps -a -q "$1")"; }

# Đầu log, phần ngay trước biểu ngữ "GARAGE VERSION" (nơi Garage in thông báo panic) và cuối log.
log_digest() {
  local out
  out="$(dc logs --no-log-prefix "$1" 2>&1)"
  head -6 <<<"$out"
  echo '[...]'
  grep -n -i -B14 'GARAGE VERSION' <<<"$out" | head -45
  echo '[...]'
  tail -5 <<<"$out"
}

stats() { # dịch vụ
  docker stats --no-stream --format 'RAM={{.MemUsage}}  CPU={{.CPUPerc}}' "$(dc ps -q "$1")"
}

exercise() { # dịch vụ
  local svc="$1" created rc
  printf '\n\n##################### %s #####################\n' "$svc"
  step "U15: tài nguyên khi rảnh" stats "$svc"
  step "U1/U2: garage status (ghi mã thoát để so với health)" g "$svc" status
  step "U1: layout do --single-node tự tạo (dung lượng, zone)" g "$svc" layout show
  step "U2: garage health (mã thoát dùng cho healthcheck)" g "$svc" health -q
  step "U3: bucket info với bucket KHÔNG tồn tại (mong đợi exit khác 0)" g "$svc" bucket info no-such-bucket
  step "U3: key info với khóa KHÔNG tồn tại (mong đợi exit khác 0)" g "$svc" key info no-such-key
  step "tạo bucket $APP_BUCKET" g "$svc" bucket create "$APP_BUCKET"
  step "U3: bucket info với bucket có tồn tại (mong đợi exit 0)" g "$svc" bucket info "$APP_BUCKET"

  printf '\n=== tạo khóa %s (bí mật giữ trong biến shell, không in)\n' "$KEY_NAME"
  created="$(g "$svc" key create "$KEY_NAME" 2>&1)"
  rc=$?
  ACCESS="$(extract_key_id <<<"$created")"
  SECRET="$(extract_secret <<<"$created")"
  printf '[exit=%s] key id=%s, độ dài secret đọc được=%s\n' "$rc" "${ACCESS:-<không đọc được>}" "${#SECRET}"
  mask_secrets <<<"$created"
  if [ -z "$ACCESS" ] || [ "${#SECRET}" -ne 64 ]; then
    echo "KHÔNG ĐỌC ĐƯỢC KHÓA từ đầu ra của 'key create': bỏ qua phần probe của $svc."
    SUMMARY+=("$svc | KHÔNG tạo/đọc được khóa | | ")
    return
  fi

  step "cấp quyền read/write/owner trên $APP_BUCKET cho khóa" g "$svc" bucket allow --read --write --owner "$APP_BUCKET" --key "$KEY_NAME"
  step "key info (không có secret) sau khi cấp quyền" g "$svc" key info "$KEY_NAME"

  # A: đúng kịch bản production (bucket tạo sẵn, khóa không có quyền tạo bucket).
  run_probe "A: khóa không có quyền tạo bucket, bucket có sẵn" "$svc" --bucket probe-a --fallback-bucket "$APP_BUCKET"

  # B: U4 — cấp quyền tạo bucket rồi thử lại.
  step "U4: key allow --create-bucket" g "$svc" key allow --create-bucket "$KEY_NAME"
  run_probe "B: khóa có --create-bucket, tự tạo/xóa bucket thử" "$svc" --bucket probe-b

  # C: bucket tạo qua S3 chỉ có alias cục bộ theo mã nguồn; giữ lại để xem `bucket list`/`bucket info` có thấy nó không.
  run_probe "C: giữ lại bucket tạo qua S3 (--keep) để xem alias" "$svc" --bucket probe-c --keep
  step "U4: bucket list (bucket tạo qua S3 có xuất hiện không?)" g "$svc" bucket list
  step "U4: bucket info probe-c theo tên (global alias?)" g "$svc" bucket info probe-c

  step "U15: tài nguyên sau khi chạy probe" stats "$svc"
  step "U3: key info sau khi chạy (khóa còn nguyên)" g "$svc" key info "$KEY_NAME"
  step "bucket $APP_BUCKET sau probe (phải trống)" g "$svc" bucket info "$APP_BUCKET"
}

echo "################ Garage spike (Slice 1, kế hoạch 15.7)"
echo "project=$PROJECT  GARAGE_IMAGE=$GARAGE_IMAGE  PROBE_IMAGE=$PROBE_IMAGE"
echo "thời điểm: $(date -Is)   docker: $(docker --version)   compose: $(docker compose version --short)"
[ -f "$PROBE_SRC" ] || { echo "Không thấy $PROBE_SRC (chạy từ repo HRMS?)"; exit 2; }
write_compose

step "kéo image Garage" docker pull "$GARAGE_IMAGE"
step "image Garage: id/digest/kích thước" docker image inspect "$GARAGE_IMAGE" --format 'id={{.Id}} size={{.Size}} digests={{.RepoDigests}} config={{json .Config}}'

# U13 + U2: 'gate' phụ thuộc garage với service_healthy; compose phải kéo garage lên, chờ healthy rồi mới chạy gate.
step "U13/U2: up gate (garage phải healthy trước khi gate chạy)" dc up -d gate
step "U13: log của gate (có dòng 'đã chạy' nghĩa là depends_on service_healthy hoạt động)" dc logs --no-log-prefix gate
step "U2/U17: khởi động garage_nofsync, chờ healthy (compose --wait)" dc up -d --wait garage_nofsync
for svc in garage garage_nofsync; do
  step "trạng thái container $svc (mã thoát, OOM)" state_of "$svc"
  if running "$svc"; then
    step "U2: trạng thái healthcheck của $svc" docker inspect --format 'status={{.State.Health.Status}} failing={{.State.Health.FailingStreak}}' "$(dc ps -q "$svc")"
  fi
  step "U9/U17: log của $svc (đầu, quanh panic nếu có, cuối)" log_digest "$svc"
done

exercise garage
if running garage_nofsync; then
  exercise garage_nofsync
else
  echo
  echo "garage_nofsync KHÔNG chạy được: bỏ qua phần probe của nó. Chẩn đoán bằng scripts/garage_spike_crash.sh"
fi

echo
echo "################ TÓM TẮT CÁC LẦN CHẠY PROBE"
printf '%s\n' "${SUMMARY[@]}"
echo "################ HẾT. Dán toàn bộ đầu ra ở trên cho người lập kế hoạch."
