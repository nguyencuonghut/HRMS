import logging
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_log = logging.getLogger(__name__)

# Giá trị default không an toàn — sẽ bị reject trong production
_UNSAFE_SECRET_KEYS = frozenset({
    "change-this-secret-key-in-production",
    "dev-secret-key-change-in-prod",
    "secret",
    "your-secret-key",
})

_UNSAFE_MINIO_CREDS = frozenset({
    "minioadmin",
    "minio",
    "password",
    "admin",
})

_UNSAFE_MINIO_ENDPOINTS = frozenset({
    "minio:9000",
})


_BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Hồng Hà HRMS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    APP_TIMEZONE: str = "Asia/Ho_Chi_Minh"

    @field_validator("APP_TIMEZONE")
    @classmethod
    def validate_app_timezone(cls, v: str) -> str:
        value = v.strip()
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("APP_TIMEZONE phải là tên múi giờ IANA hợp lệ, ví dụ Asia/Ho_Chi_Minh.") from exc
        return value

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/hrms"

    # Database connection pool (tuned for ~200 concurrent users)
    DB_POOL_SIZE:     int  = 20     # persistent connections
    DB_MAX_OVERFLOW:  int  = 40     # burst headroom
    DB_POOL_RECYCLE:  int  = 3600   # recycle every 1h, avoid idle disconnect
    DB_POOL_PRE_PING: bool = True   # validate stale connections before use

    # File upload
    MAX_UPLOAD_SIZE_MB: int = 50    # max file size for attachments

    # Monitoring
    SENTRY_DSN:               str = ""    # bỏ trống = disabled
    HEALTHCHECK_PING_URL:     str = ""    # Healthchecks.io ping URL
    SLOW_QUERY_THRESHOLD_MS:  int = 500  # log query chậm hơn ngưỡng này

    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ENCRYPTION_KEY: str = ""

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        env = (info.data.get("ENVIRONMENT") or "development").lower()
        is_prod = env == "production"

        if is_prod:
            if len(v) < 32:
                raise ValueError(
                    "SECRET_KEY phải có ít nhất 32 ký tự trong production. "
                    "Sinh key: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            if v.lower() in _UNSAFE_SECRET_KEYS:
                raise ValueError(
                    "SECRET_KEY đang dùng giá trị mặc định không an toàn. "
                    "Đặt SECRET_KEY ngẫu nhiên trong .env trước khi deploy."
                )
        elif v.lower() in _UNSAFE_SECRET_KEYS:
            _log.warning(
                "SECRET_KEY đang dùng giá trị mặc định — "
                "KHÔNG an toàn cho production. Thay bằng giá trị ngẫu nhiên."
            )
        return v

    @field_validator("ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str, info) -> str:
        env = (info.data.get("ENVIRONMENT") or "development").lower()
        if env == "production" and not v.strip():
            raise ValueError(
                "ENCRYPTION_KEY bắt buộc trong production. "
                "Sinh key: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        return v
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Refresh token cookie settings (M5)
    REFRESH_TOKEN_COOKIE_NAME: str = "refresh_token"
    # secure=True in production (HTTPS only); False in dev (HTTP)
    REFRESH_TOKEN_COOKIE_SECURE: bool = False

    @field_validator("REFRESH_TOKEN_COOKIE_SECURE")
    @classmethod
    def validate_refresh_cookie_secure(cls, v: bool, info) -> bool:
        env = (info.data.get("ENVIRONMENT") or "development").lower()
        if env == "production" and not v:
            raise ValueError(
                "REFRESH_TOKEN_COOKIE_SECURE phải = true trong production."
            )
        return v

    # Redis / Celery
    REDIS_URL:      str = "redis://localhost:6379/0"
    REDIS_PASSWORD: str = ""   # Nếu set → production mode có password

    # MinIO object storage
    MINIO_ENDPOINT:   str  = "minio:9000"
    MINIO_ACCESS_KEY: str  = "minioadmin"
    MINIO_SECRET_KEY: str  = "minioadmin"
    MINIO_BUCKET:     str  = ""
    MINIO_SECURE:     bool = False

    @model_validator(mode="after")
    def validate_minio_configuration(self) -> "Settings":
        endpoint = self.MINIO_ENDPOINT.strip().rstrip("/")
        if self.ENVIRONMENT.lower() == "production":
            if not endpoint:
                raise ValueError("MINIO_ENDPOINT bắt buộc trong production.")
            if endpoint.lower() in _UNSAFE_MINIO_ENDPOINTS:
                raise ValueError(
                    "MINIO_ENDPOINT đang dùng giá trị mặc định 'minio:9000' — "
                    "không hợp lệ cho production hiện tại. Đặt endpoint object storage thật trong .env."
                )
            if self.MINIO_ACCESS_KEY.lower() in _UNSAFE_MINIO_CREDS:
                raise ValueError(
                    "MINIO_ACCESS_KEY đang dùng giá trị mặc định 'minioadmin' — "
                    "KHÔNG an toàn cho production. Đổi trong .env."
                )
            if self.MINIO_SECRET_KEY.lower() in _UNSAFE_MINIO_CREDS:
                raise ValueError(
                    "MINIO_SECRET_KEY đang dùng giá trị mặc định 'minioadmin' — "
                    "KHÔNG an toàn cho production. Đổi trong .env."
                )
        elif self.MINIO_SECRET_KEY.lower() in _UNSAFE_MINIO_CREDS:
            _log.warning(
                "MINIO credentials đang dùng giá trị mặc định — "
                "KHÔNG an toàn cho production."
            )
        self.MINIO_ENDPOINT = endpoint
        return self

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS")
    @classmethod
    def validate_cors_origins(cls, origins: list[str], info) -> list[str]:
        env = (info.data.get("ENVIRONMENT") or "development").lower()
        normalized: list[str] = []

        for raw_origin in origins:
            origin = raw_origin.strip()
            if not origin:
                continue
            parsed = urlsplit(origin)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError(
                    "Mỗi phần tử trong CORS_ORIGINS phải là origin hợp lệ, ví dụ "
                    "'https://hrms.example.com'."
                )
            if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
                raise ValueError(
                    "CORS_ORIGINS chỉ được chứa origin thuần, không kèm path, query hoặc fragment."
                )
            normalized_origin = f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
            if normalized_origin not in normalized:
                normalized.append(normalized_origin)

        if env == "production":
            if not normalized:
                raise ValueError("CORS_ORIGINS bắt buộc phải cấu hình trong production.")
            loopback_hosts = {"localhost", "127.0.0.1", "::1"}
            if any(urlsplit(origin).hostname in loopback_hosts for origin in normalized):
                raise ValueError(
                    "CORS_ORIGINS trong production không được dùng localhost/127.0.0.1."
                )

        return normalized

    # SMTP email
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 25
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = False        # True = SMTP_SSL (port 465)
    SMTP_USE_STARTTLS: bool = False   # True = STARTTLS (port 587)
    SMTP_FROM_EMAIL: str = "no-reply@hrms.local"
    SMTP_FROM_NAME: str = "Hồng Hà HRMS"
    COMPANY_NAME: str = "Công ty Hồng Hà"

    # Backup scheduler / admin console bootstrap
    BACKUP_STORAGE_ENDPOINT: str = ""
    BACKUP_STORAGE_ACCESS_KEY: str = ""
    BACKUP_STORAGE_SECRET_KEY: str = ""
    BACKUP_STORAGE_SECURE: bool = True
    BACKUP_STORAGE_BUCKET: str = "hrms-backup"
    BACKUP_TEMP_DIR: str = "/backups/tmp"
    BACKUP_RETENTION_DAYS: int = 90
    DB_BACKUP_CRON: str = "0 2 * * *"
    MINIO_BACKUP_CRON: str = "0 3 * * *"
    SOURCE_ALIAS: str = "local"
    SOURCE_STORAGE_ENDPOINT: str = ""
    SOURCE_STORAGE_ACCESS_KEY: str = ""
    SOURCE_STORAGE_SECRET_KEY: str = ""
    SOURCE_STORAGE_SECURE: str = ""
    DEST_ALIAS: str = "backup"
    BACKUP_NOTIFY_EMAILS: str = ""

    # Administrative catalog seed source
    ADMINISTRATIVE_WARDS_JSON_PATH: str = str(
        _BASE_DIR / "app" / "seeds" / "data" / "wards_all_qd19_2025.json"
    )
    ADMINISTRATIVE_OLD_UNITS_XLSX_PATH: str = str(
        _BASE_DIR / "app" / "seeds" / "data" / "old_administrative_unit.xlsx"
    )
    ADMINISTRATIVE_OLD_UNITS_JSON_PATH: str = str(
        _BASE_DIR / "app" / "seeds" / "data" / "old_administrative_units_3_level.json"
    )
    ADMINISTRATIVE_OLD_UNITS_CONFLICTS_JSON_PATH: str = str(
        _BASE_DIR / "app" / "seeds" / "data" / "old_administrative_units_conflicts.json"
    )

    @property
    def effective_redis_url(self) -> str:
        """Trả về REDIS_URL đầy đủ.

        Nếu REDIS_URL đã chứa password (redis://:pass@...) → dùng nguyên.
        Nếu REDIS_PASSWORD được set riêng → tự inject vào URL.
        """
        url = self.REDIS_URL.strip()
        password = self.REDIS_PASSWORD.strip()

        # Đã có password trong URL → dùng nguyên
        if "@" in url:
            return url

        # Có REDIS_PASSWORD riêng → inject vào URL
        if password:
            # redis://host:port/db → redis://:password@host:port/db
            prefix = "redis://"
            if url.startswith(prefix):
                rest = url[len(prefix):]
                return f"{prefix}:{password}@{rest}"

        return url

    @property
    def minio_bucket_name(self) -> str:
        if self.MINIO_BUCKET.strip():
            return self.MINIO_BUCKET.strip()
        env_suffix = {
            "development": "dev",
            "staging": "stg",
            "production": "prod",
        }
        suffix = env_suffix.get(self.ENVIRONMENT.strip().lower(), "dev")
        return f"hrms-attachments-{suffix}"


settings = Settings()
