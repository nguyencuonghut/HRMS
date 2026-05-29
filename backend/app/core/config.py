from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Hồng Hà HRMS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/hrms"

    # Database connection pool (tuned for ~200 concurrent users)
    DB_POOL_SIZE:     int  = 20     # persistent connections
    DB_MAX_OVERFLOW:  int  = 40     # burst headroom
    DB_POOL_RECYCLE:  int  = 3600   # recycle every 1h, avoid idle disconnect
    DB_POOL_PRE_PING: bool = True   # validate stale connections before use

    # Monitoring
    SENTRY_DSN: str = ""            # bỏ trống = disabled

    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ENCRYPTION_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO object storage
    MINIO_ENDPOINT:   str  = "minio:9000"
    MINIO_ACCESS_KEY: str  = "minioadmin"
    MINIO_SECRET_KEY: str  = "minioadmin"
    MINIO_BUCKET:     str  = ""
    MINIO_SECURE:     bool = False

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

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
