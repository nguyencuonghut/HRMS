"""Tên biến kho tệp ứng dụng: S3_* là tên chính, MINIO_* vẫn được đọc làm dự phòng (kế hoạch 15.7, Slice 10).

`.env` production hiện chỉ có tên MINIO_*; cập nhật mã không được làm backend mất cấu hình kho tệp.
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


def _set(monkeypatch, prefix: str, **values: str) -> None:
    for suffix, value in values.items():
        monkeypatch.setenv(f"{prefix}_{suffix}", value)


_VALUES = dict(
    ENDPOINT="garage:3900",
    ACCESS_KEY="GKtestaccess",
    SECRET_KEY="test-secret-value-1234567890",
    BUCKET="hrms-attachments-test",
    SECURE="true",
    REGION="garage",
    BACKUP_CRON="5 4 * * *",
)


def _assert_values(cfg: Settings) -> None:
    assert cfg.S3_ENDPOINT == "garage:3900"
    assert cfg.S3_ACCESS_KEY == "GKtestaccess"
    assert cfg.S3_SECRET_KEY == "test-secret-value-1234567890"
    assert cfg.S3_BUCKET == "hrms-attachments-test"
    assert cfg.S3_SECURE is True
    assert cfg.S3_REGION == "garage"
    assert cfg.S3_BACKUP_CRON == "5 4 * * *"
    assert cfg.s3_bucket_name == "hrms-attachments-test"


def test_reads_the_new_s3_names(monkeypatch):
    _set(monkeypatch, "S3", **_VALUES)
    _assert_values(Settings(_env_file=None))


def test_still_reads_the_old_minio_names(monkeypatch):
    """Trạng thái `.env` production hiện nay: chỉ có MINIO_*."""
    _set(monkeypatch, "MINIO", **_VALUES)
    _assert_values(Settings(_env_file=None))


def test_new_names_win_when_both_are_set(monkeypatch):
    _set(monkeypatch, "MINIO", **{**_VALUES, "ENDPOINT": "old-host:9000", "BUCKET": "old-bucket"})
    _set(monkeypatch, "S3", **_VALUES)
    _assert_values(Settings(_env_file=None))


def test_production_rejects_default_credentials_and_names_the_new_variable(monkeypatch):
    base = dict(
        ENVIRONMENT="production",
        SECRET_KEY="a" * 64,
        ENCRYPTION_KEY="prod-encryption-key",
        CORS_ORIGINS=["https://hrms.example.com"],
        REFRESH_TOKEN_COOKIE_SECURE=True,
        S3_ENDPOINT="s3.example.com",
    )
    with pytest.raises(ValidationError, match="S3_ACCESS_KEY"):
        Settings(_env_file=None, S3_ACCESS_KEY="minioadmin", S3_SECRET_KEY="prod-secret-key", **base)
    with pytest.raises(ValidationError, match="S3_SECRET_KEY"):
        Settings(_env_file=None, S3_ACCESS_KEY="prod-access-key", S3_SECRET_KEY="minioadmin", **base)
    with pytest.raises(ValidationError, match="S3_ENDPOINT"):
        Settings(
            _env_file=None, S3_ACCESS_KEY="prod-access-key", S3_SECRET_KEY="prod-secret-key",
            **{**base, "S3_ENDPOINT": "minio:9000"},
        )
