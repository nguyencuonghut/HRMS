from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BhytClinicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    province_code: Optional[str] = None


class BhytClinicCreate(BaseModel):
    code: str = Field(max_length=20)
    name: str = Field(max_length=255)
    province_code: Optional[str] = Field(None, max_length=10)


class BhytClinicUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    province_code: Optional[str] = Field(None, max_length=10)


class BhytClinicListPage(BaseModel):
    items: list[BhytClinicRead]
    total: int
    page: int
    page_size: int
