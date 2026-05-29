"""Schemas cho Notification module."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TemplateUpdate(BaseModel):
    subject: Optional[str] = None
    body_html: Optional[str] = None
    is_active: Optional[bool] = None


class PreviewRequest(BaseModel):
    sample_data: dict[str, str] = {}


class PreviewResponse(BaseModel):
    html: str


class ConfigUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    extra_recipients: Optional[list[str]] = None


class TestSendRequest(BaseModel):
    template_code: str
    recipient_email: str


class TemplateResponse(BaseModel):
    id: int
    code: str
    event_type: str
    name: str
    subject: str
    body_html: str
    body_text: Optional[str]
    merge_fields: list
    is_active: bool
    is_system: bool
    days_before: Optional[int]
    recipient_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConfigResponse(BaseModel):
    id: int
    event_type: str
    is_enabled: bool
    days_before: Optional[list[int]]
    extra_recipients: Optional[list[str]]
    updated_at: datetime

    model_config = {"from_attributes": True}


class LogItem(BaseModel):
    id: int
    template_code: Optional[str]
    event_type: str
    employee_id: Optional[int]
    recipient_email: str
    recipient_name: Optional[str]
    subject: Optional[str]
    status: str
    error_message: Optional[str]
    sent_at: datetime
    celery_task_id: Optional[str]

    model_config = {"from_attributes": True}


class LogListResponse(BaseModel):
    items: list[LogItem]
    total: int
    page: int
    page_size: int
    total_pages: int
