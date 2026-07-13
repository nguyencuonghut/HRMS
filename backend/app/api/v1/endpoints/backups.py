"""Backup & Restore Admin Console API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.backup import (
    BackupConfigResponse,
    BackupConfigUpdate,
    BackupMetaResponse,
    BackupOption,
    BackupOverviewResponse,
    BackupStatusOption,
    BackupValidateTargetRequest,
    BackupValidateTargetResponse,
)
from app.services import auth_service, backup_service

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


@router.put("/config/{kind}", response_model=BackupConfigResponse)
async def update_backup_config(
    kind: str,
    payload: BackupConfigUpdate,
    request: Request,
    current_user: User = require_permission("backups:edit"),
    session: AsyncSession = Depends(get_session),
) -> BackupConfigResponse:
    try:
        row, old_data, new_data = await backup_service.update_backup_config(
            session,
            kind=kind,
            payload=payload,
            user_id=current_user.id,
        )
    except backup_service.BackupConfigNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy cấu hình sao lưu",
        ) from exc

    await auth_service.log_audit(
        session,
        current_user.id,
        "UPDATE",
        entity_type="backup_config",
        entity_id=row.id,
        entity_name=row.kind,
        old_data=old_data,
        new_data=new_data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    return backup_service.config_response(row)


@router.post("/validate-target", response_model=BackupValidateTargetResponse)
async def validate_backup_target(
    payload: BackupValidateTargetRequest,
    current_user: User = require_permission("backups:edit"),
    session: AsyncSession = Depends(get_session),
) -> BackupValidateTargetResponse:
    try:
        _, result = await backup_service.validate_backup_target(
            session,
            kind=payload.kind,
            user_id=current_user.id,
        )
    except backup_service.BackupConfigNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy cấu hình sao lưu",
        ) from exc

    await session.commit()
    return result


@router.get("/overview", response_model=BackupOverviewResponse)
async def get_backup_overview(
    _: User = require_permission("backups:view"),
    session: AsyncSession = Depends(get_session),
) -> BackupOverviewResponse:
    return await backup_service.get_backup_overview(session)
