"""Backup & Restore Admin Console API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi import Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.backup import (
    BackupConfigResponse,
    BackupConfigUpdate,
    BackupJobCreateRequest,
    BackupJobSummary,
    BackupMetaResponse,
    BackupOption,
    BackupOverviewResponse,
    BackupSetSummary,
    BackupSnapshotSummary,
    BackupStatusOption,
    RestoreRequestCreate,
    RestoreRequestSummary,
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


@router.post("/jobs", response_model=BackupJobSummary, status_code=status.HTTP_201_CREATED)
async def create_manual_backup_job(
    payload: BackupJobCreateRequest,
    request: Request,
    current_user: User = require_permission("backups:create"),
    session: AsyncSession = Depends(get_session),
) -> BackupJobSummary:
    try:
        row = await backup_service.create_manual_backup_job(
            session,
            kind=payload.kind,
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
        "CREATE",
        entity_type="backup_job",
        entity_id=row.id,
        entity_name=row.kind,
        new_data=backup_service.safe_job_snapshot(row),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    backup_service.enqueue_backup_job(row.id)
    return backup_service.job_response(row)


@router.post("/sets", response_model=BackupSetSummary, status_code=status.HTTP_201_CREATED)
async def create_manual_backup_set(
    request: Request,
    current_user: User = require_permission("backups:create"),
    session: AsyncSession = Depends(get_session),
) -> BackupSetSummary:
    try:
        row = await backup_service.create_manual_backup_set(
            session,
            user_id=current_user.id,
        )
    except backup_service.BackupConfigNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy cấu hình sao lưu",
        ) from exc
    except backup_service.ActiveBackupSetExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Đã có bộ sao lưu đầy đủ #{exc.backup_set_id} đang chờ hoặc đang chạy. "
                "Vui lòng đợi tác vụ hiện tại hoàn tất trước khi tạo bộ mới."
            ),
        ) from exc

    await auth_service.log_audit(
        session,
        current_user.id,
        "CREATE",
        entity_type="backup_set",
        entity_id=row.id,
        entity_name=f"backup-set-{row.id}",
        new_data=backup_service.safe_backup_set_snapshot(row),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    backup_service.enqueue_backup_set(row.id)
    return await backup_service.get_backup_set_summary(session, row.id)


@router.get("/jobs", response_model=list[BackupJobSummary])
async def list_backup_jobs(
    kind: str | None = None,
    job_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    _: User = require_permission("backups:view"),
    session: AsyncSession = Depends(get_session),
) -> list[BackupJobSummary]:
    return await backup_service.list_backup_jobs(
        session,
        kind=kind,
        status=job_status,
        limit=limit,
    )


@router.get("/sets", response_model=list[BackupSetSummary])
async def list_backup_sets(
    backup_set_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    _: User = require_permission("backups:view"),
    session: AsyncSession = Depends(get_session),
) -> list[BackupSetSummary]:
    return await backup_service.list_backup_sets(
        session,
        status=backup_set_status,
        limit=limit,
    )


@router.get("/snapshots", response_model=list[BackupSnapshotSummary])
async def list_backup_snapshots(
    kind: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    _: User = require_permission("backups:view"),
    session: AsyncSession = Depends(get_session),
) -> list[BackupSnapshotSummary]:
    return await backup_service.list_backup_snapshots(
        session,
        kind=kind,
        limit=limit,
    )


@router.post("/restore-requests", response_model=RestoreRequestSummary, status_code=status.HTTP_201_CREATED)
async def create_restore_request(
    payload: RestoreRequestCreate,
    request: Request,
    current_user: User = require_permission("backups:create"),
    session: AsyncSession = Depends(get_session),
) -> RestoreRequestSummary:
    try:
        row = await backup_service.create_restore_request(
            session,
            kind=payload.kind,
            mode=payload.mode,
            backup_set_id=payload.backup_set_id,
            db_artifact_key=payload.db_artifact_key,
            object_snapshot_key=payload.object_snapshot_key,
            target_db_name=payload.target_db_name,
            target_bucket=payload.target_bucket,
            confirmation_text=payload.confirmation_text,
            notes=payload.notes,
            user_id=current_user.id,
        )
    except backup_service.BackupSnapshotNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy artifact sao lưu để khôi phục",
        ) from exc
    except backup_service.BackupSetNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy bộ sao lưu đầy đủ để khôi phục",
        ) from exc
    except backup_service.UnsafeRestoreTarget as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await auth_service.log_audit(
        session,
        current_user.id,
        "CREATE",
        entity_type="restore_request",
        entity_id=row.id,
        entity_name=row.kind,
        new_data=backup_service.safe_restore_snapshot(row),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await session.commit()
    backup_service.enqueue_restore_request(row.id)
    return RestoreRequestSummary.model_validate(row)


@router.get("/restore-requests", response_model=list[RestoreRequestSummary])
async def list_restore_requests(
    kind: str | None = None,
    restore_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    _: User = require_permission("backups:view"),
    session: AsyncSession = Depends(get_session),
) -> list[RestoreRequestSummary]:
    return await backup_service.list_restore_requests(
        session,
        kind=kind,
        status=restore_status,
        limit=limit,
    )


@router.get("/overview", response_model=BackupOverviewResponse)
async def get_backup_overview(
    _: User = require_permission("backups:view"),
    session: AsyncSession = Depends(get_session),
) -> BackupOverviewResponse:
    return await backup_service.get_backup_overview(session)
