from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    from datetime import timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BhytClinic(SQLModel, table=True):
    """Danh mục cơ sở khám chữa bệnh ban đầu BHYT.

    Seed từ sheet 'BenhVien' trong FileMau_D02_TK1_VNPT.xlsx (~12,822 entries).
    """

    __tablename__ = "bhyt_clinics"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(max_length=20, unique=True, index=True)
    name: str = Field(max_length=255)
    province_code: Optional[str] = Field(default=None, max_length=10, index=True)
    province_name: Optional[str] = Field(default=None, max_length=100)
