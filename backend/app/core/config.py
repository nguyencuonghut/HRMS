from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Hồng Hà HRMS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/hrms"

    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO object storage
    MINIO_ENDPOINT:   str  = "minio:9000"
    MINIO_ACCESS_KEY: str  = "minioadmin"
    MINIO_SECRET_KEY: str  = "minioadmin"
    MINIO_BUCKET:     str  = "hrms-attachments"
    MINIO_SECURE:     bool = False

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

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


settings = Settings()
