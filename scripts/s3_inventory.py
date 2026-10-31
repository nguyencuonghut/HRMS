"""Kiểm kê object storage (chỉ đọc), kế hoạch 15.7, Phụ lục D.

Chạy bằng chính container backend (đã có SDK và biến môi trường kết nối), từ thư mục gốc repo:

    docker compose -f docker-compose.lan.yml exec -T backend python - < scripts/s3_inventory.py

Chỉ đọc cấu hình từ S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, S3_SECURE, S3_REGION (tên cũ MINIO_* vẫn được đọc); không import gì từ ứng dụng;
không in khóa. Chỉ in ba tên object (cắt ngắn) cho mỗi bucket vì tên có thể chứa dữ liệu cá nhân.
"""
import os
import sys
from collections import Counter

from minio import Minio

MIB5 = 5 * 1024 * 1024


def env(suffix, default=None):
    """S3_<suffix> là tên chính; MINIO_<suffix> là tên cũ vẫn được đọc (kế hoạch 15.7, Slice 10)."""
    v = os.environ.get(f"S3_{suffix}", os.environ.get(f"MINIO_{suffix}", default))
    if v is None or v == "":
        sys.exit(f"missing env var S3_{suffix}")
    return v


endpoint = env("ENDPOINT")
secure = os.environ.get("S3_SECURE", os.environ.get("MINIO_SECURE", "false")).strip().lower() in ("1", "true", "yes", "on")
region = os.environ.get("S3_REGION", os.environ.get("MINIO_REGION", "")).strip() or None   # Garage cần region; MinIO thì không
client = Minio(endpoint, access_key=env("ACCESS_KEY"), secret_key=env("SECRET_KEY"), secure=secure, region=region)

print(f"endpoint={endpoint} secure={secure} region={region}")
buckets = client.list_buckets()
print(f"buckets={len(buckets)}")
g_count = g_bytes = 0
for b in sorted(buckets, key=lambda x: x.name):
    count = total = big = non_ascii = 0
    prefixes = Counter()
    top = []
    for o in client.list_objects(b.name, recursive=True):
        if o.is_dir:
            continue
        size = o.size or 0
        count += 1
        total += size
        if size > MIB5:
            big += 1
        if not o.object_name.isascii():
            non_ascii += 1
        prefixes[o.object_name.split("/", 1)[0] if "/" in o.object_name else "(root)"] += 1
        top.append((size, o.object_name))
    top.sort(reverse=True)
    g_count += count
    g_bytes += total
    print(f"\n[bucket] {b.name}")
    print(f"  objects={count} total_bytes={total} (~{total / 1048576:.2f} MiB)")
    print(f"  objects_gt_5MiB={big} non_ascii_names={non_ascii}")
    print("  top3_largest:")
    for size, name in top[:3]:
        print(f"    {size:>12}  {name[:60]!r}")
    print("  top_level_prefixes:")
    for p, c in prefixes.most_common():
        print(f"    {p[:60]!r}: {c}")
print(f"\nTOTAL objects={g_count} bytes={g_bytes} (~{g_bytes / 1048576:.2f} MiB)")
