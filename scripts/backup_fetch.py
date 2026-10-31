#!/usr/bin/env python3
"""Lấy artifact sao lưu từ Garage bằng SDK Python (đường khôi phục thủ công, không cần Backup Console).

Chạy trong container backend (đã có SDK `minio` và các biến môi trường), từ thư mục gốc repo:

    DC="docker compose -f docker-compose.lan.yml"
    $DC exec -T backend python - list [PREFIX]                         < scripts/backup_fetch.py
    $DC exec -T backend python - get KEY                               < scripts/backup_fetch.py > tep.sql.gz
    $DC exec -T backend python - restore-files SNAPSHOT_PREFIX BUCKET  < scripts/backup_fetch.py
    $DC exec -T backend python - delete-bucket BUCKET                  < scripts/backup_fetch.py

  list           liệt kê khóa, kích thước, thời điểm sửa trong kho sao lưu (BACKUP_STORAGE_BUCKET); PREFIX tùy chọn.
  get            ghi nguyên văn một object ra stdout (nhị phân), dùng cho dump DB `postgres/hrms_*.sql.gz` hoặc một tệp
                 trong snapshot `files/files-*/...`.
  restore-files  chép mọi object của một snapshot kho tệp (trừ manifest.json) sang BUCKET mới. BUCKET phải CHƯA tồn tại
                 (giống Backup Console: không bao giờ ghi đè vào kho có sẵn); script tạo bucket bằng khóa ứng dụng.
  delete-bucket  xóa mọi object rồi xóa BUCKET, để dọn kho thử sau khi kiểm tra khôi phục. Từ chối nếu BUCKET trùng
                 MINIO_BUCKET hoặc BACKUP_STORAGE_BUCKET (kho đang dùng). Không hoàn tác được.

Khóa sao lưu (BACKUP_STORAGE_*) dùng để đọc kho sao lưu; khóa ứng dụng (MINIO_*) dùng để tạo và ghi bucket đích.
Không bao giờ in giá trị bí mật. Thông báo đi ra stderr để stdout của `get` chỉ có dữ liệu.
"""
from __future__ import annotations

import os
import sys

from minio import Minio
from minio.error import S3Error


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def client(prefix: str) -> Minio:
    endpoint = env(f"{prefix}_ENDPOINT")
    if not endpoint:
        sys.exit(f"LỖI: thiếu {prefix}_ENDPOINT trong môi trường")
    secure = env(f"{prefix}_SECURE", "false").lower() in ("1", "true", "yes", "on")
    return Minio(
        endpoint,
        access_key=env(f"{prefix}_ACCESS_KEY"),
        secret_key=env(f"{prefix}_SECRET_KEY"),
        secure=secure,
        region=env(f"{prefix}_REGION") or None,
    )


def backup_client() -> tuple[Minio, str]:
    return client("BACKUP_STORAGE"), env("BACKUP_STORAGE_BUCKET", "hrms-backup")


def cmd_list(args: list[str]) -> int:
    source, bucket = backup_client()
    prefix = args[0] if args else ""
    count = 0
    for item in source.list_objects(bucket, prefix=prefix, recursive=True):
        print(f"{item.size or 0:>12}  {item.last_modified:%Y-%m-%d %H:%M:%S}  {item.object_name}")
        count += 1
    print(f"{count} object trong {bucket}/{prefix}", file=sys.stderr)
    return 0


def cmd_get(args: list[str]) -> int:
    if len(args) != 1:
        sys.exit("LỖI: get cần đúng một KEY")
    source, bucket = backup_client()
    response = source.get_object(bucket, args[0])
    written = 0
    try:
        for chunk in response.stream(1024 * 1024):
            sys.stdout.buffer.write(chunk)
            written += len(chunk)
    finally:
        response.close()
        response.release_conn()
    sys.stdout.buffer.flush()
    print(f"đã ghi {written} byte từ {bucket}/{args[0]}", file=sys.stderr)
    return 0


def cmd_restore_files(args: list[str]) -> int:
    if len(args) != 2:
        sys.exit("LỖI: restore-files cần SNAPSHOT_PREFIX và BUCKET")
    snapshot, target_bucket = args[0].rstrip("/"), args[1]
    source, bucket = backup_client()
    target = client("MINIO")
    if target.bucket_exists(target_bucket):
        sys.exit(f"LỖI: kho đích {target_bucket} đã tồn tại; hãy chọn tên kho mới. Không ghi đè.")
    items = [i for i in source.list_objects(bucket, prefix=f"{snapshot}/", recursive=True)
             if i.object_name[len(snapshot) + 1:] not in ("", "manifest.json")]
    if not items:
        sys.exit(f"LỖI: không có object dữ liệu dưới {bucket}/{snapshot}/ (sai tiền tố?)")
    target.make_bucket(target_bucket)
    copied = total = 0
    for item in items:
        relative = item.object_name[len(snapshot) + 1:]
        response = source.get_object(bucket, item.object_name)
        try:
            target.put_object(target_bucket, relative, response, length=item.size or 0,
                              content_type=getattr(item, "content_type", None) or "application/octet-stream")
        finally:
            response.close()
            response.release_conn()
        copied += 1
        total += item.size or 0
    print(f"đã chép {copied} tệp ({total} byte) vào kho mới {target_bucket}", file=sys.stderr)
    return 0


def cmd_delete_bucket(args: list[str]) -> int:
    if len(args) != 1:
        sys.exit("LỖI: delete-bucket cần đúng một BUCKET")
    name = args[0]
    in_use = {env("MINIO_BUCKET"), env("BACKUP_STORAGE_BUCKET", "hrms-backup")}
    if name in in_use:
        sys.exit(f"LỖI: {name} đang được cấu hình dùng (MINIO_BUCKET hoặc BACKUP_STORAGE_BUCKET); không xóa.")
    target = client("MINIO")
    if not target.bucket_exists(name):
        sys.exit(f"LỖI: không thấy kho {name}")
    removed = 0
    for item in target.list_objects(name, recursive=True):
        target.remove_object(name, item.object_name)
        removed += 1
    target.remove_bucket(name)
    print(f"đã xóa {removed} object và kho {name}", file=sys.stderr)
    return 0


COMMANDS = {"list": cmd_list, "get": cmd_get, "restore-files": cmd_restore_files, "delete-bucket": cmd_delete_bucket}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(f"Dùng: {' | '.join(COMMANDS)} (xem phần đầu tệp)")
    try:
        return COMMANDS[sys.argv[1]](sys.argv[2:])
    except S3Error as exc:
        sys.exit(f"LỖI S3 ({exc.code}): {exc.message}")


if __name__ == "__main__":
    sys.exit(main())
