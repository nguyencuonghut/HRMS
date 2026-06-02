"""MinIO object storage helper."""
from __future__ import annotations

import uuid
from io import BytesIO
from pathlib import Path
from typing import Generator

from fastapi import HTTPException, UploadFile, status
from minio import Minio
from minio.error import S3Error

from app.core.circuit_breaker import CircuitOpenError, minio_circuit
from app.core.config import settings

# ── File validation constants ─────────────────────────────────────────────────

MAX_UPLOAD_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf", ".xlsx", ".xls", ".docx", ".doc",
    ".jpg", ".jpeg", ".png", ".webp",
}

ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/vnd.ms-excel",
    "image/jpeg",
    "image/png",
    "image/webp",
}

ALTERNATE_CONTENT_TYPES_BY_EXTENSION = {
    ".docx": {
        "application/wps-office.docx",
        "application/octet-stream",
    },
    ".xlsx": {
        "application/octet-stream",
    },
    ".doc": {
        "application/octet-stream",
    },
    ".xls": {
        "application/octet-stream",
    },
}


def validate_file_type(upload: UploadFile) -> None:
    """Kiểm tra extension và content-type. Raise 400 nếu không hợp lệ."""
    ext = Path(upload.filename or "").suffix.lower()
    ct = (upload.content_type or "").split(";")[0].strip().lower()

    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng file không được phép: {ext}. Chỉ chấp nhận: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    allowed_alternates = ALTERNATE_CONTENT_TYPES_BY_EXTENSION.get(ext, set())
    if ct and ct not in ALLOWED_CONTENT_TYPES and ct not in allowed_alternates and not ct.startswith("image/"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Content-type không hợp lệ: {ct}",
        )


async def validate_upload(upload: UploadFile, *, check_type: bool = True) -> bytes:
    """Đọc file và validate kích thước + loại. Raise HTTPException nếu vi phạm."""
    if check_type:
        validate_file_type(upload)

    content = await upload.read()

    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File quá lớn ({len(content) / 1024 / 1024:.1f} MB). Tối đa {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )
    if len(content) == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="File rỗng, vui lòng kiểm tra lại.",
        )
    return content


def _client() -> Minio:
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )


@minio_circuit.call
def _minio_put(object_name: str, data: BytesIO, length: int, content_type: str) -> None:
    """Circuit-protected MinIO put. Raises CircuitOpenError khi MinIO đang down."""
    _client().put_object(
        bucket_name=bucket_name(),
        object_name=object_name,
        data=data,
        length=length,
        content_type=content_type,
    )


@minio_circuit.call
def _minio_get(object_name: str):  # type: ignore[return]
    """Circuit-protected MinIO get. Raises CircuitOpenError khi MinIO đang down."""
    return _client().get_object(bucket_name(), object_name)


def bucket_name() -> str:
    return settings.minio_bucket_name


def ensure_bucket() -> None:
    """Tạo bucket nếu chưa tồn tại. Gọi một lần khi khởi động."""
    client = _client()
    if not client.bucket_exists(bucket_name()):
        client.make_bucket(bucket_name())


async def save_employee_attachment(employee_id: int, upload: UploadFile) -> tuple[str, int]:
    """
    Upload file hồ sơ nhân viên lên MinIO.
    Trả về (object_name, file_size).
    """
    content = await validate_upload(upload)
    safe_name = Path(upload.filename or "file").name
    object_name = f"employees/{employee_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"

    try:
        _minio_put(object_name, BytesIO(content), len(content), content_type)
    except CircuitOpenError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    return object_name, len(content)


async def save_attachment(position_id: int, upload: UploadFile) -> tuple[str, int]:
    """
    Upload file lên MinIO.
    Trả về (object_name, file_size).
    """
    content = await validate_upload(upload)
    safe_name = Path(upload.filename or "file").name
    object_name = f"attachments/{position_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"

    try:
        _minio_put(object_name, BytesIO(content), len(content), content_type)
    except CircuitOpenError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    return object_name, len(content)


def get_object_stream(object_name: str) -> Generator[bytes, None, None]:
    """Stream object từ MinIO, dùng cho StreamingResponse."""
    try:
        response = _minio_get(object_name)
    except CircuitOpenError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    try:
        yield from response
    finally:
        response.close()
        response.release_conn()


def get_object_bytes(object_name: str) -> bytes:
    """Tải toàn bộ object từ MinIO về bytes. Dùng cho xử lý in-memory (DOCX inspection)."""
    try:
        response = _minio_get(object_name)
    except CircuitOpenError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


async def save_contract_file(contract_id: int, upload: UploadFile) -> tuple[str, int]:
    """Upload file hợp đồng (scan/PDF) lên MinIO. Trả về (object_name, file_size)."""
    content = await validate_upload(upload)
    safe_name = Path(upload.filename or "file").name
    object_name = f"contracts/{contract_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"
    try:
        _minio_put(object_name, BytesIO(content), len(content), content_type)
    except CircuitOpenError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    return object_name, len(content)


async def save_template_file(template_id: int, upload: UploadFile) -> tuple[str, int]:
    """Upload file DOCX mẫu hợp đồng lên MinIO. Trả về (object_name, file_size)."""
    content = await validate_upload(upload)
    safe_name = Path(upload.filename or "template.docx").name
    object_name = f"templates/{template_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    try:
        _minio_put(object_name, BytesIO(content), len(content), content_type)
    except CircuitOpenError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    return object_name, len(content)


async def save_reward_file(reward_id: int, upload: UploadFile) -> tuple[str, int]:
    """Upload file quyết định khen thưởng lên MinIO. Trả về (object_name, file_size)."""
    content = await validate_upload(upload)
    safe_name = Path(upload.filename or "file").name
    object_name = f"rewards/{reward_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"
    try:
        _minio_put(object_name, BytesIO(content), len(content), content_type)
    except CircuitOpenError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    return object_name, len(content)


async def save_discipline_file(discipline_id: int, upload: UploadFile) -> tuple[str, int]:
    """Upload file quyết định kỷ luật lên MinIO. Trả về (object_name, file_size)."""
    content = await validate_upload(upload)
    safe_name = Path(upload.filename or "file").name
    object_name = f"disciplines/{discipline_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"
    try:
        _minio_put(object_name, BytesIO(content), len(content), content_type)
    except CircuitOpenError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    return object_name, len(content)


async def save_certificate_file(cert_id: int, upload: UploadFile) -> tuple[str, int]:
    """Upload file chứng chỉ lên MinIO. Trả về (object_name, file_size)."""
    content = await validate_upload(upload)
    safe_name = Path(upload.filename or "file").name
    object_name = f"certificates/{cert_id}/{uuid.uuid4().hex[:8]}_{safe_name}"
    content_type = upload.content_type or "application/octet-stream"
    try:
        _minio_put(object_name, BytesIO(content), len(content), content_type)
    except CircuitOpenError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)) from e
    return object_name, len(content)


def delete_attachment(object_name: str) -> None:
    """Xóa object khỏi MinIO; bỏ qua nếu không tồn tại."""
    try:
        _client().remove_object(bucket_name(), object_name)
    except S3Error:
        pass
