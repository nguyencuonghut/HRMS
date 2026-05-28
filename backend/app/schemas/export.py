from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


ReportType = Literal[
    "dashboard",
    "hr-employee-list",
    "hr-movement",
    "hr-tenure",
    "hr-org-structure",
    "leaves",
    "insurance",
    "contracts",
    "recruitment",
    "probation",
]
ExportFormat = Literal["xlsx", "pdf"]
ExportStatus = Literal["pending", "processing", "done", "failed"]


class ExportJobRequest(BaseModel):
    report_type: ReportType
    format: ExportFormat = "xlsx"
    filters: dict[str, Any] = Field(default_factory=dict)
    filename: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def sanitize_filename(self) -> "ExportJobRequest":
        if self.filename:
            self.filename = re.sub(r'[\\/:*?"<>|]+', "_", self.filename).strip()
            if not self.filename:
                self.filename = None
        return self


class ExportJobResponse(BaseModel):
    id: uuid.UUID
    report_type: str
    format: str
    status: ExportStatus
    filename: Optional[str]
    file_size_bytes: Optional[int]
    row_count: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]
    download_url: Optional[str] = None

    model_config = {"from_attributes": True}


class ExportJobStatusResponse(BaseModel):
    id: uuid.UUID
    status: ExportStatus
    progress_pct: Optional[int] = None
    error_message: Optional[str] = None
    download_url: Optional[str] = None


class ExportHistoryResponse(BaseModel):
    items: list[ExportJobResponse]
    total: int
    page: int
    page_size: int


class ReportTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    report_type: ReportType
    format: ExportFormat = "xlsx"
    filters: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class ReportTemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    filters: Optional[dict[str, Any]] = None
    format: Optional[ExportFormat] = None
    is_default: Optional[bool] = None


class ReportTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    report_type: str
    format: str
    filters: dict[str, Any]
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
