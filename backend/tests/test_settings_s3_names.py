"""Tên biến kho tệp ứng dụng là S3_*; tên cũ MINIO_* không còn được đọc (kế hoạch 15.7, Slice 10).

Tên cũ đã được gỡ sau khi `.env` production đổi sang S3_*. Gỡ mà không báo lỗi thì một `.env` còn tên cũ sẽ chạy
ngầm bằng giá trị mặc định; ở production, giá trị mặc định bị validator từ chối nên backend không khởi động và
thông báo nêu đúng tên mới cần đặt.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

_SUFFIXES = ("ENDPOINT", "ACCESS_KEY", "SECRET_KEY", "BUCKET", "SECURE", "REGION", "BACKUP_CRON")


@pytest.fixture(autouse=True)
def clean_storage_env(monkeypatch):
    for suffix in _SUFFIXES:
        monkeypatch.delenv(f"S3_{suffix}", raising=False)
        monkeypatch.delenv(f"MINIO_{suffix}", raising=False)


_VALUES = dict(
    ENDPOINT="garage:3900",
    ACCESS_KEY="GKtestaccess",
    SECRET_KEY="test-secret-value-1234567890",
    BUCKET="hrms-attachments-test",
    SECURE="true",
    REGION="garage",
    BACKUP_CRON="5 4 * * *",
)

_PRODUCTION = dict(
    ENVIRONMENT="production",
    SECRET_KEY="a" * 64,
    ENCRYPTION_KEY="prod-encryption-key",
    CORS_ORIGINS=["https://hrms.example.com"],
    REFRESH_TOKEN_COOKIE_SECURE=True,
)


def test_reads_the_s3_names(monkeypatch):
    for suffix, value in _VALUES.items():
        monkeypatch.setenv(f"S3_{suffix}", value)

    cfg = Settings(_env_file=None)

    assert cfg.S3_ENDPOINT == "garage:3900"
    assert cfg.S3_ACCESS_KEY == "GKtestaccess"
    assert cfg.S3_SECRET_KEY == "test-secret-value-1234567890"
    assert cfg.S3_BUCKET == "hrms-attachments-test"
    assert cfg.S3_SECURE is True
    assert cfg.S3_REGION == "garage"
    assert cfg.S3_BACKUP_CRON == "5 4 * * *"
    assert cfg.s3_bucket_name == "hrms-attachments-test"


def test_the_old_minio_names_are_no_longer_read(monkeypatch):
    for suffix, value in _VALUES.items():
        monkeypatch.setenv(f"MINIO_{suffix}", value)

    cfg = Settings(_env_file=None)

    assert cfg.S3_ENDPOINT == "minio:9000"          # mặc định, không phải garage:3900
    assert cfg.S3_ACCESS_KEY == "minioadmin"
    assert cfg.S3_BUCKET == ""
    assert cfg.S3_REGION == ""
    assert cfg.S3_BACKUP_CRON == "0 3 * * *"


def test_production_with_only_the_old_names_refuses_to_start_and_names_the_new_variable(monkeypatch):
    for suffix in ("ENDPOINT", "ACCESS_KEY", "SECRET_KEY"):
        monkeypatch.setenv(f"MINIO_{suffix}", _VALUES[suffix])

    with pytest.raises(ValidationError, match="S3_ENDPOINT"):
        Settings(_env_file=None, **_PRODUCTION)


def test_production_rejects_default_credentials_and_names_the_variable():
    base = {**_PRODUCTION, "S3_ENDPOINT": "s3.example.com"}
    with pytest.raises(ValidationError, match="S3_ACCESS_KEY"):
        Settings(_env_file=None, S3_ACCESS_KEY="minioadmin", S3_SECRET_KEY="prod-secret-key", **base)
    with pytest.raises(ValidationError, match="S3_SECRET_KEY"):
        Settings(_env_file=None, S3_ACCESS_KEY="prod-access-key", S3_SECRET_KEY="minioadmin", **base)
    with pytest.raises(ValidationError, match="S3_ENDPOINT"):
        Settings(
            _env_file=None, S3_ACCESS_KEY="prod-access-key", S3_SECRET_KEY="prod-secret-key",
            **{**base, "S3_ENDPOINT": "minio:9000"},
        )
