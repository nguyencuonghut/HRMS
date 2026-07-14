from __future__ import annotations

from datetime import datetime
import re
from typing import Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator


_BUCKET_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_cron_part(raw: str, minimum: int, maximum: int) -> bool:
    for item in raw.split(","):
        if not item:
            return False

        base, separator, step = item.partition("/")
        if separator:
            if not step.isdigit() or int(step) < 1:
                return False
        if base == "*":
            continue

        start_raw, range_separator, end_raw = base.partition("-")
        if not start_raw.isdigit():
            return False
        start = int(start_raw)
        if not minimum <= start <= maximum:
            return False

        if range_separator:
            if not end_raw.isdigit():
                return False
            end = int(end_raw)
            if not minimum <= end <= maximum or end < start:
                return False

    return True


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _validate_backup_object_key(value: str) -> str:
    cleaned = value.strip().strip("/")
    if not cleaned:
        raise ValueError("đường dẫn artifact là bắt buộc")
    if "\\" in cleaned or any(part in {"", ".."} for part in cleaned.split("/")):
        raise ValueError("đường dẫn artifact không hợp lệ")
    return cleaned


class BackupOption(BaseModel):
    code: str
    label: str
    order: int


class BackupStatusOption(BaseModel):
    code: str
    label: str
    severity: str
    order: int


class BackupMetaResponse(BaseModel):
    kinds: list[BackupOption]
    job_statuses: list[BackupStatusOption]
    restore_statuses: list[BackupStatusOption]


class BackupConfigResponse(BaseModel):
    id: int
    kind: str
    kind_label: str
    enabled: bool
    cron_expression: str
    retention_days: int
    source_endpoint: Optional[str]
    source_bucket: Optional[str]
    source_secure: Optional[bool]
    target_endpoint: Optional[str]
    target_bucket: str
    target_prefix: Optional[str]
    target_secure: bool
    notify_emails: Optional[list[str]]
    secret_source: str
    source_configured: bool
    target_configured: bool
    last_validated_at: Optional[datetime]
    last_validation_status: Optional[str]
    last_validation_error: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BackupConfigUpdate(BaseModel):
    enabled: bool
    cron_expression: str = Field(min_length=9, max_length=100)
    retention_days: int = Field(ge=1, le=3650)
    source_endpoint: Optional[str] = Field(default=None, max_length=255)
    source_bucket: Optional[str] = Field(default=None, max_length=255)
    source_secure: Optional[bool] = None
    target_endpoint: Optional[str] = Field(default=None, max_length=255)
    target_bucket: str = Field(min_length=3, max_length=63)
    target_prefix: Optional[str] = Field(default=None, max_length=255)
    target_secure: bool
    notify_emails: Optional[list[str]] = None

    @field_validator("cron_expression")
    @classmethod
    def validate_cron_expression(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        parts = cleaned.split(" ")
        if len(parts) != 5:
            raise ValueError("Lịch chạy phải có đúng 5 trường")
        ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
        if not all(_validate_cron_part(part, minimum, maximum) for part, (minimum, maximum) in zip(parts, ranges)):
            raise ValueError("Lịch chạy không hợp lệ")
        return cleaned

    @field_validator("source_endpoint", "target_endpoint")
    @classmethod
    def validate_endpoint(cls, value: str | None) -> str | None:
        cleaned = _strip_optional(value)
        if cleaned is None:
            return None
        if "@" in cleaned or any(ch.isspace() for ch in cleaned):
            raise ValueError("địa chỉ kết nối không được chứa thông tin xác thực hoặc khoảng trắng")
        if "://" in cleaned:
            parsed = urlsplit(cleaned)
            if not parsed.netloc:
                raise ValueError("địa chỉ kết nối không hợp lệ")
            cleaned = parsed.netloc
        return cleaned.rstrip("/")

    @field_validator("source_bucket")
    @classmethod
    def validate_optional_bucket(cls, value: str | None) -> str | None:
        cleaned = _strip_optional(value)
        if cleaned is None:
            return None
        return cls._validate_bucket(cleaned)

    @field_validator("target_bucket")
    @classmethod
    def validate_target_bucket(cls, value: str) -> str:
        return cls._validate_bucket(value.strip())

    @classmethod
    def _validate_bucket(cls, value: str) -> str:
        if not _BUCKET_RE.match(value) or ".." in value or ".-" in value or "-." in value:
            raise ValueError("kho lưu trữ MinIO/S3 không hợp lệ")
        return value

    @field_validator("target_prefix")
    @classmethod
    def validate_target_prefix(cls, value: str | None) -> str | None:
        cleaned = _strip_optional(value)
        if cleaned is None:
            return None
        cleaned = cleaned.strip("/")
        if not cleaned:
            return None
        if "\\" in cleaned or any(part in {"", ".."} for part in cleaned.split("/")):
            raise ValueError("thư mục đích không hợp lệ")
        return cleaned

    @field_validator("notify_emails")
    @classmethod
    def validate_notify_emails(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        emails: list[str] = []
        for raw_email in value:
            email = raw_email.strip().lower()
            if not email:
                continue
            if len(email) > 254 or not _EMAIL_RE.match(email):
                raise ValueError("Danh sách thư điện tử nhận thông báo chứa địa chỉ không hợp lệ")
            if email not in emails:
                emails.append(email)
        return emails or None


class BackupValidateTargetRequest(BaseModel):
    kind: str

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in {"db", "object_storage"}:
            raise ValueError("Loại cấu hình sao lưu không hợp lệ")
        return cleaned


class BackupValidateTargetResponse(BaseModel):
    kind: str
    status: str
    message: str
    checked_at: datetime
    target_configured: bool


class BackupJobCreateRequest(BaseModel):
    kind: str

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in {"db", "object_storage"}:
            raise ValueError("Loại cấu hình sao lưu không hợp lệ")
        return cleaned


class BackupJobSummary(BaseModel):
    id: int
    backup_set_id: Optional[int]
    kind: str
    trigger: str
    status: str
    artifact_key: Optional[str]
    artifact_bucket: Optional[str]
    artifact_size_bytes: Optional[int]
    object_count: Optional[int]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_summary: Optional[str]
    log_excerpt: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class BackupSnapshotSummary(BaseModel):
    kind: str
    artifact_key: str
    artifact_bucket: str
    artifact_size_bytes: Optional[int]
    object_count: Optional[int]
    created_at: datetime
    finished_at: Optional[datetime]


class BackupSetSummary(BaseModel):
    id: int
    trigger: str
    status: str
    db_job_id: Optional[int]
    object_job_id: Optional[int]
    db_artifact_key: Optional[str]
    object_snapshot_key: Optional[str]
    artifact_bucket: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_summary: Optional[str]
    created_at: datetime
    updated_at: datetime


class RestoreRequestCreate(BaseModel):
    kind: str
    mode: str
    backup_set_id: Optional[int] = Field(default=None, ge=1)
    db_artifact_key: Optional[str] = Field(default=None, max_length=500)
    object_snapshot_key: Optional[str] = Field(default=None, max_length=500)
    target_db_name: Optional[str] = Field(default=None, max_length=63)
    target_bucket: Optional[str] = Field(default=None, min_length=3, max_length=63)
    confirmation_text: str = Field(min_length=5, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in {"db", "object_storage", "full"}:
            raise ValueError("Loại yêu cầu khôi phục không hợp lệ")
        return cleaned

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in {"verify_only", "restore_to_new_target"}:
            raise ValueError("Chế độ khôi phục không hợp lệ")
        return cleaned

    @field_validator("db_artifact_key", "object_snapshot_key")
    @classmethod
    def validate_artifact_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_backup_object_key(value)

    @field_validator("target_db_name")
    @classmethod
    def validate_target_db_name(cls, value: str | None) -> str | None:
        cleaned = _strip_optional(value)
        if cleaned is None:
            return None
        if not re.match(r"^[a-z][a-z0-9_]{2,62}$", cleaned):
            raise ValueError("Tên cơ sở dữ liệu đích chỉ dùng chữ thường, số và dấu gạch dưới")
        return cleaned

    @field_validator("target_bucket")
    @classmethod
    def validate_target_bucket(cls, value: str | None) -> str | None:
        cleaned = _strip_optional(value)
        if cleaned is None:
            return None
        return BackupConfigUpdate._validate_bucket(cleaned)

    @field_validator("confirmation_text")
    @classmethod
    def validate_confirmation_text(cls, value: str) -> str:
        cleaned = " ".join(value.strip().split())
        if len(cleaned) < 5:
            raise ValueError("Cần nhập nội dung xác nhận khôi phục")
        return cleaned

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: str | None) -> str | None:
        return _strip_optional(value)

    @model_validator(mode="after")
    def validate_required_fields(self) -> "RestoreRequestCreate":
        if self.kind == "full":
            if not self.backup_set_id:
                raise ValueError("Cần chọn bộ sao lưu đầy đủ")
        if self.kind == "db" and not self.db_artifact_key:
            raise ValueError("Cần chọn bản sao lưu cơ sở dữ liệu")
        if self.kind == "object_storage" and not self.object_snapshot_key:
            raise ValueError("Cần chọn snapshot kho tệp ứng dụng")
        if self.mode == "restore_to_new_target":
            if self.kind in {"db", "full"} and not self.target_db_name:
                raise ValueError("Cần nhập cơ sở dữ liệu đích mới")
            if self.kind in {"object_storage", "full"} and not self.target_bucket:
                raise ValueError("Cần nhập kho tệp đích mới")
        return self


class RestoreRequestSummary(BaseModel):
    id: int
    backup_set_id: Optional[int]
    kind: str
    mode: str
    status: str
    db_artifact_key: Optional[str]
    object_snapshot_key: Optional[str]
    target_db_name: Optional[str]
    target_bucket: Optional[str]
    requested_by_id: Optional[int]
    approved_by_id: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BackupOverviewResponse(BaseModel):
    config_count: int
    configs: list[BackupConfigResponse]
    latest_jobs: list[BackupJobSummary]
    latest_backup_sets: list[BackupSetSummary]
    latest_restore_requests: list[RestoreRequestSummary]
