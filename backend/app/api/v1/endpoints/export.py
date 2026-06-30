from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.export_catalog import (
    EXPORT_FORMAT_DEFS,
    EXPORT_FORMAT_ORDER,
    EXPORT_STATUS_DEFS,
    EXPORT_STATUS_ORDER,
    REPORT_DEFS,
    REPORT_TYPE_ORDER,
)
from app.core.database import get_session
from app.models.auth import User
from app.schemas.export import (
    ExportHistoryResponse,
    ExportFormatOption,
    ExportJobRequest,
    ExportJobResponse,
    ExportJobStatusResponse,
    ExportMetaResponse,
    ExportReportTypeOption,
    ExportStatusOption,
    ReportTemplateCreate,
    ReportTemplateResponse,
    ReportTemplateUpdate,
)
from app.services.export_service import ExportService

router = APIRouter()


@router.get("/meta", response_model=ExportMetaResponse)
async def get_export_meta(
    _: User = require_permission("reports:view"),
) -> ExportMetaResponse:
    return ExportMetaResponse(
        report_types=[
            ExportReportTypeOption(code=code, label=label, order=REPORT_TYPE_ORDER[code])
            for code, label in REPORT_DEFS
        ],
        formats=[
            ExportFormatOption(code=code, label=label, order=EXPORT_FORMAT_ORDER[code])
            for code, label in EXPORT_FORMAT_DEFS
        ],
        statuses=[
            ExportStatusOption(code=code, label=label, severity=severity, order=EXPORT_STATUS_ORDER[code])
            for code, label, severity in EXPORT_STATUS_DEFS
        ],
    )


@router.post("", response_model=ExportJobResponse)
async def create_export_job(
    payload: ExportJobRequest,
    current_user: User = require_permission("reports:export"),
    session: AsyncSession = Depends(get_session),
) -> ExportJobResponse:
    service = ExportService(session)
    job = await service.create_export_job(payload, current_user)
    return service._to_response(job)


@router.get("/history", response_model=ExportHistoryResponse)
async def get_export_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = require_permission("reports:view"),
    session: AsyncSession = Depends(get_session),
) -> ExportHistoryResponse:
    return await ExportService(session).get_history(current_user, page=page, page_size=page_size)


@router.get("/{job_id}/status", response_model=ExportJobStatusResponse)
async def get_export_status(
    job_id: uuid.UUID,
    current_user: User = require_permission("reports:view"),
    session: AsyncSession = Depends(get_session),
) -> ExportJobStatusResponse:
    return await ExportService(session).get_status(job_id, current_user)


@router.get("/{job_id}/download")
async def download_export(
    job_id: uuid.UUID,
    current_user: User = require_permission("reports:export"),
    session: AsyncSession = Depends(get_session),
):
    job = await ExportService(session).get_download_job(job_id, current_user)
    media_type = "application/pdf" if job.format == "pdf" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(
        Path(job.file_path),
        media_type=media_type,
        filename=job.filename,
    )


@router.delete("/{job_id}", status_code=204)
async def delete_export_job(
    job_id: uuid.UUID,
    current_user: User = require_permission("reports:export"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await ExportService(session).delete_job(job_id, current_user)
    return Response(status_code=204)


@router.post("/templates", response_model=ReportTemplateResponse)
async def create_report_template(
    payload: ReportTemplateCreate,
    current_user: User = require_permission("reports:export"),
    session: AsyncSession = Depends(get_session),
) -> ReportTemplateResponse:
    return await ExportService(session).create_template(payload, current_user)


@router.get("/templates", response_model=list[ReportTemplateResponse])
async def list_report_templates(
    current_user: User = require_permission("reports:view"),
    session: AsyncSession = Depends(get_session),
) -> list[ReportTemplateResponse]:
    return await ExportService(session).list_templates(current_user)


@router.put("/templates/{template_id}", response_model=ReportTemplateResponse)
async def update_report_template(
    template_id: int,
    payload: ReportTemplateUpdate,
    current_user: User = require_permission("reports:export"),
    session: AsyncSession = Depends(get_session),
) -> ReportTemplateResponse:
    return await ExportService(session).update_template(template_id, payload, current_user)


@router.delete("/templates/{template_id}", status_code=204)
async def delete_report_template(
    template_id: int,
    current_user: User = require_permission("reports:export"),
    session: AsyncSession = Depends(get_session),
) -> Response:
    await ExportService(session).delete_template(template_id, current_user)
    return Response(status_code=204)
