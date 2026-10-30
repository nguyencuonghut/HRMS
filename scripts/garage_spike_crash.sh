#!/usr/bin/env bash
# garage_spike_crash.sh — Slice 1 (kế hoạch 15.7): tìm nguyên nhân instance Garage cấu hình
# "fsync tắt + snapshot mỗi 1 phút" bị crash (mã thoát 139, panic trong MerkleWorker) ở lần chạy đầu.
#
# CHỈ CHẠY TRÊN MÁY DEV. Mỗi biến thể chạy riêng một container (volume riêng, không dùng mạng),
# bị loại bỏ ngay sau khi xong. Không có khóa truy cập nào được tạo hay in ra.
#
# Dùng (từ thư mục gốc repo):
#   bash scripts/garage_spike_crash.sh 2>&1 | tee /tmp/garage_spike_crash.out            # bộ "crash", ~3 phút
#   bash scripts/garage_spike_crash.sh snapshot 2>&1 | tee /tmp/garage_spike_snapshot.out # bộ "snapshot", ~8 phút
#
# Biến tùy chọn:
#   GARAGE_IMAGE  image Garage cần thử (mặc định: dxflrs/garage:v2.5.0)
#   PROBE_IMAGE   image có `ls` để liệt kê volume (mặc định: hrms-backend:latest)
#   WAIT          số giây theo dõi mỗi biến thể trong bộ "crash" có snapshot 1 phút (mặc định 90; biến thể khác 30)
#   KEEP=1        không xóa container/volume của biến thể cuối (để xem thủ công)
#
# Biến thể (fsync, snapshot):
#   A  true   6h     đối chứng: đúng Phụ lục A (đã chạy ổn ở lần trước)
#   B  false  tắt    chỉ tắt fsync
#   C  true   1min   chỉ bật snapshot 1 phút
#   D  false  1min   cấu hình đã crash (chạy 2 lần để xem có tái hiện đều không)
#
# Kết quả đã có (2026-10-30): bộ "crash" cho thấy C, D1, D2 (chu kỳ 1min) crash mã 139 còn A, B chạy ổn, tức không
# phải do fsync. Bộ "snapshot" cho thấy nguyên nhân là chu kỳ nhỏ hơn 600 giây (mã nguồn v2.5.0: `interval <
# from_secs(600)` trả lỗi "too small or negative"): 60s bị từ chối sạch, 1min và 2min crash, 10min và 1h chạy tốt.
# Chi tiết ở mục "Kết quả Slice 1" trong docs/plan_15.7_chuyen_minio_sang_garage.md.
#
# Bộ "snapshot" (fsync bật, như Phụ lục A) thử các chu kỳ khác nhau và lệnh snapshot thủ công:
#   M    không đặt chu kỳ, gọi `garage meta snapshot` thủ công rồi xem thư mục snapshots
#   I60  chu kỳ "60s" (cùng độ dài với 1min nhưng viết khác đơn vị)
#   I2   chu kỳ "2min"
#   I10  chu kỳ "10min", theo dõi 330 giây để thấy lần snapshot đầu (lên lịch sau nửa chu kỳ, tức khoảng 5 phút)
#   I1H  chu kỳ "1h"

set -uo pipefail
cd "$(dirname "$0")/.."

GARAGE_IMAGE="${GARAGE_IMAGE:-dxflrs/garage:v2.5.0}"
PROBE_IMAGE="${PROBE_IMAGE:-hrms-backend:latest}"
WAIT="${WAIT:-90}"

rand_hex() { od -An -N"$1" -tx1 /dev/urandom | tr -d ' \n'; }

TAG="g157crash$(rand_hex 4)"
WORK="$(mktemp -d)"
GARAGE_RPC_SECRET="$(rand_hex 32)"
GARAGE_ADMIN_TOKEN="$(rand_hex 32)"
export GARAGE_RPC_SECRET GARAGE_ADMIN_TOKEN
CURRENT=""

mask_secrets() { sed -e "s/$GARAGE_RPC_SECRET/<đã ẩn>/g" -e "s/$GARAGE_ADMIN_TOKEN/<đã ẩn>/g"; }

drop_variant() {
  [ -n "$CURRENT" ] || return 0
  docker rm -f "$CURRENT" >/dev/null 2>&1
  docker volume rm -f "${CURRENT}_meta" "${CURRENT}_data" >/dev/null 2>&1
  CURRENT=""
}
cleanup() {
  if [ "${KEEP:-0}" = "1" ] && [ -n "$CURRENT" ]; then
    echo "KEEP=1: giữ lại container $CURRENT và volume ${CURRENT}_meta, ${CURRENT}_data. Dọn thủ công khi xong."
  else
    drop_variant
  fi
  rm -rf "$WORK"
}
trap cleanup EXIT

write_toml() { # file fsync snapshot ("" = tắt)
  {
    cat <<TOML
metadata_dir = "/var/lib/garage/meta"
data_dir = "/var/lib/garage/data"

db_engine = "sqlite"
metadata_fsync = $2
data_fsync = $2
TOML
    [ -n "$3" ] && echo "metadata_auto_snapshot_interval = \"$3\""
    cat <<'TOML'

replication_factor = 1

rpc_bind_addr = "0.0.0.0:3901"
rpc_public_addr = "127.0.0.1:3901"

[s3_api]
s3_region = "garage"
api_bind_addr = "0.0.0.0:3900"

[admin]
api_bind_addr = "0.0.0.0:3903"
TOML
  } >"$1"
}

variant() { # nhãn fsync snapshot thời_gian_theo_dõi [lệnh_garage_chạy_sau_khi_khởi_động]
  local label="$1" fsync="$2" snap="$3" wait_s="$4" after="${5:-}" waited=0 state snaplines
  CURRENT="${TAG}_${label}"
  printf '\n\n##################### biến thể %s: fsync=%s snapshot=%s (theo dõi tối đa %ss)\n' "$label" "$fsync" "${snap:-tắt}" "$wait_s"
  write_toml "$WORK/$label.toml" "$fsync" "$snap"

  docker run -d --name "$CURRENT" -e GARAGE_RPC_SECRET -e GARAGE_ADMIN_TOKEN \
    -v "$WORK/$label.toml:/etc/garage.toml:ro" \
    -v "${CURRENT}_meta:/var/lib/garage/meta" -v "${CURRENT}_data:/var/lib/garage/data" \
    "$GARAGE_IMAGE" /garage server --single-node >/dev/null 2>&1 \
    || { echo "KHÔNG khởi động được container"; drop_variant; return; }

  while [ "$waited" -lt "$wait_s" ]; do
    sleep 5
    waited=$((waited + 5))
    state="$(docker inspect --format '{{.State.Status}}' "$CURRENT")"
    [ "$state" = "running" ] || break
    if [ -n "$after" ]; then
      echo "--- sau ${waited}s chạy: /garage $after"
      # shellcheck disable=SC2086
      docker exec "$CURRENT" /garage $after 2>&1 | mask_secrets | tail -8
      echo "exit=${PIPESTATUS[0]}"
      after=""
    fi
  done

  echo "--- trạng thái sau ${waited}s:"
  docker inspect --format 'state={{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}} error={{.State.Error}} started={{.State.StartedAt}} finished={{.State.FinishedAt}}' "$CURRENT"

  if [ "$state" = "running" ]; then
    echo "--- garage health -q (mã thoát):"
    docker exec "$CURRENT" /garage health -q >/dev/null 2>&1
    echo "exit=$?"
    echo "--- thư mục metadata (có snapshots không?):"
    docker run --rm -v "${CURRENT}_meta:/m:ro" --entrypoint ls "$PROBE_IMAGE" -laR /m 2>&1
  fi

  echo "--- log: đầu, phần ngay trước biểu ngữ 'GARAGE VERSION' (thông báo panic), và cuối:"
  docker logs "$CURRENT" 2>&1 | mask_secrets >"$WORK/$label.log"
  head -4 "$WORK/$label.log"
  echo "[...]"
  grep -n -i -B16 'GARAGE VERSION' "$WORK/$label.log" | head -50
  echo "[...]"
  tail -4 "$WORK/$label.log"
  echo "--- dòng log nhắc snapshot:"
  snaplines="$(grep -i snapshot "$WORK/$label.log" | head -5)"
  if [ -n "$snaplines" ]; then echo "$snaplines"; else echo "(không có)"; fi

  [ "${KEEP:-0}" = "1" ] && [ "$label" = "D2" ] && return
  drop_variant
}

echo "################ Garage crash isolation (Slice 1, kế hoạch 15.7)"
echo "image=$GARAGE_IMAGE  thời điểm: $(date -Is)"
echo "kernel: $(uname -r)   CPU: $(grep -m1 'model name' /proc/cpuinfo | cut -d: -f2- | sed 's/^ //')"
echo "docker: $(docker --version)   storage: $(docker info --format '{{.Driver}} / driver-status={{.DriverStatus}}' 2>/dev/null)"
docker image inspect "$GARAGE_IMAGE" >/dev/null 2>&1 || { echo "Chưa có image $GARAGE_IMAGE: chạy 'docker pull $GARAGE_IMAGE' trước."; exit 2; }
echo "digest: $(docker image inspect "$GARAGE_IMAGE" --format '{{index .RepoDigests 0}}')"

case "${1:-crash}" in
  crash)
    variant A true 6h 30
    variant B false "" 30
    variant C true 1min "$WAIT"
    variant D1 false 1min "$WAIT"
    variant D2 false 1min "$WAIT"
    ;;
  snapshot)
    variant M true "" 20 "meta snapshot"
    variant I60 true 60s 20
    variant I2 true 2min 20
    variant I10 true 10min 330
    variant I1H true 1h 20
    ;;
  *) echo "Bộ không hợp lệ: ${1}. Dùng 'crash' hoặc 'snapshot'."; exit 2 ;;
esac

echo
echo "################ HẾT. Dán toàn bộ đầu ra ở trên cho người lập kế hoạch."
