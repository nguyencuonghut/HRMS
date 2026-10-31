"""Nơi duy nhất tạo client S3 của ứng dụng (kế hoạch 15.7, Slice 10)."""
from __future__ import annotations

from minio import Minio
from urllib3 import PoolManager, Timeout


def build_s3_client(
    endpoint: str,
    access_key: str,
    secret_key: str,
    secure: bool,
    region: str | None = None,
    *,
    timeout: tuple[float, float] | None = None,
) -> Minio:
    """Tạo client S3.

    `region` rỗng hoặc None nghĩa là để SDK tự dò (MinIO). Garage từ chối chữ ký có region khác `s3_region` và SDK không tự
    sửa được, nên với Garage phải truyền `region="garage"`.
    `timeout` là (chờ kết nối, chờ đọc) tính bằng giây, không thử lại; None thì dùng client HTTP mặc định của SDK.
    """
    http_client = (
        PoolManager(timeout=Timeout(connect=timeout[0], read=timeout[1]), retries=False) if timeout else None
    )
    return Minio(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
        region=region or None,
        http_client=http_client,
    )
