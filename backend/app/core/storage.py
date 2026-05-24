"""MinIO object storage helper."""
from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path
from typing import Generator

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from app.core.config import settings


def _client() -> Minio:
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


def ensure_bucket() -> None:
    """Tạo bucket nếu chưa tồn tại. Gọi một lần khi khởi động."""
    client = _client()
    if not client.bucket_exists(settings.MINIO_BUCKET):
        client.make_bucket(settings.MINIO_BUCKET)


async def save_employee_attachment(employee_id: int, upload: UploadFile) -> tuple[str, int]:
    """
    Upload file hồ sơ nhân viên lên MinIO.
    Trả về (object_name, file_size).
    """
    content = await upload.read()
    safe_name = Path(upload.filename or "file").name
    object_name = f"employees/{employee_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"

    _client().put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return object_name, len(content)


async def save_attachment(position_id: int, upload: UploadFile) -> tuple[str, int]:
    """
    Upload file lên MinIO.
    Trả về (object_name, file_size).
    """
    content = await upload.read()
    safe_name = Path(upload.filename or "file").name
    object_name = f"attachments/{position_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"

    _client().put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return object_name, len(content)


def get_object_stream(object_name: str) -> Generator[bytes, None, None]:
    """Stream object từ MinIO, dùng cho StreamingResponse."""
    response = _client().get_object(settings.MINIO_BUCKET, object_name)
    try:
        yield from response
    finally:
        response.close()
        response.release_conn()


def get_object_bytes(object_name: str) -> bytes:
    """Tải toàn bộ object từ MinIO về bytes. Dùng cho xử lý in-memory (DOCX inspection)."""
    response = _client().get_object(settings.MINIO_BUCKET, object_name)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


async def save_contract_file(contract_id: int, upload: UploadFile) -> tuple[str, int]:
    """Upload file hợp đồng (scan/PDF) lên MinIO. Trả về (object_name, file_size)."""
    content = await upload.read()
    safe_name = Path(upload.filename or "file").name
    object_name = f"contracts/{contract_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"
    _client().put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return object_name, len(content)


async def save_template_file(template_id: int, upload: UploadFile) -> tuple[str, int]:
    """Upload file DOCX mẫu hợp đồng lên MinIO. Trả về (object_name, file_size)."""
    content = await upload.read()
    safe_name = Path(upload.filename or "template.docx").name
    object_name = f"templates/{template_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    _client().put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return object_name, len(content)


async def save_reward_file(reward_id: int, upload: UploadFile) -> tuple[str, int]:
    """Upload file quyết định khen thưởng lên MinIO. Trả về (object_name, file_size)."""
    content = await upload.read()
    safe_name = Path(upload.filename or "file").name
    object_name = f"rewards/{reward_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"
    _client().put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return object_name, len(content)


async def save_discipline_file(discipline_id: int, upload: UploadFile) -> tuple[str, int]:
    """Upload file quyết định kỷ luật lên MinIO. Trả về (object_name, file_size)."""
    content = await upload.read()
    safe_name = Path(upload.filename or "file").name
    object_name = f"disciplines/{discipline_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"
    _client().put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return object_name, len(content)


async def save_certificate_file(cert_id: int, upload: UploadFile) -> tuple[str, int]:
    """Upload file chứng chỉ lên MinIO. Trả về (object_name, file_size)."""
    content = await upload.read()
    safe_name = Path(upload.filename or "file").name
    object_name = f"certificates/{cert_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"
    _client().put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=object_name,
        data=BytesIO(content),
        length=len(content),
        content_type=content_type,
    )
    return object_name, len(content)


def delete_attachment(object_name: str) -> None:
    """Xóa object khỏi MinIO; bỏ qua nếu không tồn tại."""
    try:
        _client().remove_object(settings.MINIO_BUCKET, object_name)
    except S3Error:
        pass
