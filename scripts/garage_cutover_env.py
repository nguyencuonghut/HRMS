#!/usr/bin/env python3
"""Chuyển .env sang Garage (kế hoạch 15.7, runbook mục 10.2 bước 1).

Dùng, từ thư mục gốc repo trên máy chủ:

    python3 scripts/garage_cutover_env.py /tmp/garage_keys.env            # thực hiện
    python3 scripts/garage_cutover_env.py /tmp/garage_keys.env --dry-run  # chỉ báo cáo, không ghi

`/tmp/garage_keys.env` là đầu ra stdout của scripts/garage_bootstrap.sh (đúng 4 dòng khóa).

Việc script làm:
  - sao lưu .env ra thư mục home (quyền 600) trước khi sửa;
  - đặt S3_ENDPOINT, S3_BUCKET, S3_REGION, S3_SECURE, BACKUP_STORAGE_ENDPOINT, BACKUP_STORAGE_REGION,
    BACKUP_STORAGE_SECURE (thay dòng có sẵn, thêm nếu chưa có, bỏ dòng trùng). Dòng tên cũ MINIO_* (trước Slice 10) được đổi
    thành tên S3_* tại chỗ, để `.env` không có hai bộ tên song song;
  - xóa 4 dòng khóa cũ rồi nối 4 khóa Garage ở cuối file;
  - đặt quyền .env là 600 và ghi nguyên tử (tệp tạm rồi đổi tên).

Không bao giờ in giá trị bí mật (chỉ in tên biến, và giá trị cũ/mới của các biến KHÔNG bí mật như endpoint, bucket). Chạy lại với
cùng khóa cho ra đúng cùng một .env. Dừng (mã 2) và không sửa gì nếu: khóa không đúng định dạng, thiếu GARAGE_RPC_SECRET hoặc
GARAGE_ADMIN_TOKEN trong .env. Dòng chú thích (bắt đầu bằng #) không bao giờ bị đụng tới.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

KEY_NAMES = ("S3_ACCESS_KEY", "S3_SECRET_KEY", "BACKUP_STORAGE_ACCESS_KEY", "BACKUP_STORAGE_SECRET_KEY")
# Tên cũ (trước Slice 10, kế hoạch 15.7): tệp khóa vẫn được chấp nhận theo tên cũ; trong .env chúng được đổi sang tên mới.
LEGACY_KEY_NAMES = {"MINIO_ACCESS_KEY": "S3_ACCESS_KEY", "MINIO_SECRET_KEY": "S3_SECRET_KEY"}
LEGACY_SCALAR_NAMES = {"MINIO_ENDPOINT": "S3_ENDPOINT", "MINIO_BUCKET": "S3_BUCKET", "MINIO_REGION": "S3_REGION", "MINIO_SECURE": "S3_SECURE"}
LEGACY_OF = {new: old for old, new in LEGACY_SCALAR_NAMES.items()}
REQUIRED_GARAGE_VARS = ("GARAGE_RPC_SECRET", "GARAGE_ADMIN_TOKEN")
SOURCE_OVERRIDES = ("SOURCE_STORAGE_ENDPOINT", "SOURCE_STORAGE_ACCESS_KEY", "SOURCE_STORAGE_SECRET_KEY", "SOURCE_STORAGE_SECURE")
LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
KEY_BLOCK_MARKER = "# Garage: khóa do scripts/garage_bootstrap.sh sinh"


def fail(message: str) -> "None":
    print(f"LỖI: {message}", file=sys.stderr)
    sys.exit(2)


def read_new_keys(path: Path) -> dict[str, str]:
    if not path.is_file():
        fail(f"không thấy tệp khóa {path}")
    keys: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        match = LINE.match(raw)
        name = LEGACY_KEY_NAMES.get(match.group(1), match.group(1)) if match else None
        if name not in KEY_NAMES or name in keys:
            fail(f"{path} phải có đúng 4 dòng {', '.join(KEY_NAMES)} (mỗi tên một lần)")
        keys[name] = match.group(2)
    if set(keys) != set(KEY_NAMES):
        fail(f"{path} thiếu khóa: {', '.join(sorted(set(KEY_NAMES) - set(keys)))}")
    for name in ("S3_ACCESS_KEY", "BACKUP_STORAGE_ACCESS_KEY"):
        if not re.fullmatch(r"GK[0-9a-f]{24,}", keys[name]):
            fail(f"{name} không đúng dạng khóa Garage (GK + chuỗi hex)")
    for name in ("S3_SECRET_KEY", "BACKUP_STORAGE_SECRET_KEY"):
        if not re.fullmatch(r"[0-9a-f]{64}", keys[name]):
            fail(f"{name} không đúng dạng secret Garage (64 ký tự hex)")
    return keys


def main() -> int:
    parser = argparse.ArgumentParser(description="Chuyển .env sang Garage, không in bí mật.")
    parser.add_argument("keys_file", type=Path, help="đầu ra stdout của scripts/garage_bootstrap.sh (4 dòng khóa)")
    parser.add_argument("--env", type=Path, default=Path(".env"), help="tệp .env cần sửa (mặc định: ./.env)")
    parser.add_argument("--bucket", default="hrms-attachments-prod", help="S3_BUCKET mới (mặc định: hrms-attachments-prod)")
    parser.add_argument("--backup-dir", type=Path, default=Path.home(), help="nơi cất bản sao lưu .env (mặc định: thư mục home)")
    parser.add_argument("--dry-run", action="store_true", help="chỉ báo cáo, không ghi gì")
    args = parser.parse_args()

    keys = read_new_keys(args.keys_file)
    if not args.env.is_file():
        fail(f"không thấy {args.env}")
    lines = args.env.read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()

    current: dict[str, str] = {}
    for raw in lines:
        match = LINE.match(raw)
        if match:
            current[match.group(1)] = match.group(2)

    missing = [name for name in REQUIRED_GARAGE_VARS if not current.get(name, "").strip()]
    if missing:
        fail(f"{args.env} chưa có {', '.join(missing)} (runbook 10.1 bước 1). Không sửa gì.")

    scalars = {
        "S3_ENDPOINT": "garage:3900",
        "S3_BUCKET": args.bucket,
        "S3_REGION": "garage",
        "S3_SECURE": "false",
        "BACKUP_STORAGE_ENDPOINT": "garage:3900",
        "BACKUP_STORAGE_REGION": "garage",
        "BACKUP_STORAGE_SECURE": "false",
    }

    result: list[str] = []
    seen: set[str] = set()
    removed_keys = 0
    for raw in lines:
        if raw.startswith(KEY_BLOCK_MARKER):
            continue                          # dấu của chính script ở lần chạy trước; ghi lại ở cuối
        match = LINE.match(raw)
        name = match.group(1) if match else None
        if name in KEY_NAMES or name in LEGACY_KEY_NAMES:
            removed_keys += 1
            continue
        if name in LEGACY_SCALAR_NAMES:
            name = LEGACY_SCALAR_NAMES[name]      # tên cũ: đổi tại chỗ sang tên S3_*
            raw = f"{name}={scalars[name]}"
            if name in seen:
                continue
            seen.add(name)
            result.append(raw)
            continue
        if name in scalars:
            if name in seen:
                continue                      # bỏ dòng trùng
            seen.add(name)
            raw = f"{name}={scalars[name]}"
        result.append(raw)
    added = [name for name in scalars if name not in seen]
    while result and result[-1] == "":
        result.pop()
    result.append("")
    if added:
        result.append("# Garage: các biến thêm bởi scripts/garage_cutover_env.py")
        result += [f"{name}={scalars[name]}" for name in added]
        result.append("")
    result.append(f"{KEY_BLOCK_MARKER} (hrms-app cho S3_*, hrms-backup cho BACKUP_STORAGE_*)")
    result += [f"{name}={keys[name]}" for name in KEY_NAMES]
    new_text = "\n".join(result) + "\n"

    print(f"{'[dry-run] ' if args.dry_run else ''}Kết quả cho {args.env}:")
    for name, value in scalars.items():
        old = current.get(name, current.get(LEGACY_OF.get(name, "")))
        print(f"  {name}: {old if old is not None else '(chưa có)'} -> {value}")
    print(f"  khóa cũ đã bỏ: {removed_keys} dòng; khóa Garage mới nối: {len(KEY_NAMES)} dòng ({', '.join(KEY_NAMES)}); giá trị không được in")
    overrides = [name for name in SOURCE_OVERRIDES if current.get(name, "").strip()]
    if overrides:
        print(f"  CẢNH BÁO: {', '.join(overrides)} đang được đặt trong .env. Các biến này ghi đè nguồn sao lưu kho tệp; kiểm tra tay "
              "(kế hoạch giả định chúng để trống).")

    if args.dry_run:
        print("  (dry-run: chưa ghi gì)")
        return 0

    backup = args.backup_dir / f"hrms_env_before_garage_{time.strftime('%Y%m%d-%H%M%S')}"
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle, open(args.env, "rb") as source:
        shutil.copyfileobj(source, handle)
    tmp_fd, tmp_name = tempfile.mkstemp(dir=args.env.resolve().parent, prefix=".env.tmp.")
    with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
        handle.write(new_text)
    os.chmod(tmp_name, 0o600)
    os.replace(tmp_name, args.env)
    print(f"  đã ghi {args.env} (quyền 600). Bản gốc: {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
