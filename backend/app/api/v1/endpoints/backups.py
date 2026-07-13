"""Backup & Restore Admin Console API."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.backup import (
    BackupConfigResponse,
    BackupMetaResponse,
    BackupOption,
    BackupOverviewResponse,
    BackupStatusOption,
)
from app.services import backup_service

router = APIRouter()


@router.get("/meta", response_model=BackupMetaResponse)
async def get_backup_meta(
    _: User = require_permission("backups:view"),
) -> BackupMetaResponse:
    return BackupMetaResponse(
        kinds=[
            BackupOption(code=code, label=label, order=index)
            for index, (code, label) in enumerate(backup_service.BACKUP_KIND_DEFS, start=1)
        ],
        job_statuses=[
            BackupStatusOption(code=code, label=label, severity=severity, order=index)
            for index, (code, label, severity) in enumerate(backup_service.JOB_STATUS_DEFS, start=1)
        ],
        restore_statuses=[
            BackupStatusOption(code=code, label=label, severity=severity, order=index)
            for index, (code, label, severity) in enumerate(backup_service.RESTORE_STATUS_DEFS, start=1)
        ],
    )


@router.get("/config", response_model=list[BackupConfigResponse])
async def list_backup_config(
    _: User = require_permission("backups:view"),
    session: AsyncSession = Depends(get_session),
) -> list[BackupConfigResponse]:
    return await backup_service.list_backup_configs(session)


@router.get("/overview", response_model=BackupOverviewResponse)
async def get_backup_overview(
    _: User = require_permission("backups:view"),
    session: AsyncSession = Depends(get_session),
) -> BackupOverviewResponse:
    return await backup_service.get_backup_overview(session)

