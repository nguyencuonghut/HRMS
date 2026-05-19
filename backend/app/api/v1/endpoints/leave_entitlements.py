from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.leave_entitlement import (
    BulkAllocateRequest,
    BulkAllocateResult,
    LeaveEntitlementCreate,
    LeaveEntitlementRead,
    LeaveEntitlementUpdate,
)
from app.services import auth_service, leave_entitlement_service
from pydantic import BaseModel


class LeaveEntitlementListPage(BaseModel):
    items: list[LeaveEntitlementRead]
    total: int
    page: int
    page_size: int


router = APIRouter()


def _meta(request: Request) -> tuple[str | None, str | None]:
    return (
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


# ── Phải khai báo trước /{id} để tránh FastAPI nhầm literal path ─────────────

@router.post(
    "/bulk-allocate",
    response_model=BulkAllocateResult,
    summary="Nạp phép hàng loạt",
)
async def bulk_allocate(
    body: BulkAllocateRequest,
    request: Request,
    current_user: User = require_permission("leaves:create"),
    session: AsyncSession = Depends(get_session),
):
    result = await leave_entitlement_service.bulk_allocate(session, body, current_user.id)
    ip, ua = _meta(request)
    await auth_service.log_audit(
        session, current_user.id, "BULK_ALLOCATE",
        entity_type="leave_entitlement", entity_id=None,
        entity_name=f"bulk-allocate year={body.year}",
        new_data={"year": body.year, "allocated": result.allocated, "skipped": result.skipped},
        ip_address=ip, user_agent=ua,
    )
    return result


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=LeaveEntitlementListPage, summary="Danh sách ngày phép")
async def list_entitlements(
    employee_id:   Optional[int] = Query(None),
    year:          Optional[int] = Query(None),
    leave_type_id: Optional[int] = Query(None),
    keyword:       Optional[str] = Query(None),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(20, ge=1, le=200),
    _: User = require_permission("leaves:view"),
    session: AsyncSession = Depends(get_session),
):
    return await leave_entitlement_service.list_entitlements(
        session,
        employee_id=employee_id,
        year=year,
        leave_type_id=leave_type_id,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=LeaveEntitlementRead, status_code=status.HTTP_201_CREATED, summary="Thêm ngày phép thủ công")
async def create_entitlement(
    body: LeaveEntitlementCreate,
    request: Request,
    current_user: User = require_permission("leaves:create"),
    session: AsyncSession = Depends(get_session),
):
    row = await leave_entitlement_service.create_entitlement(session, body, current_user.id)
    ip, ua = _meta(request)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="leave_entitlement", entity_id=row.id,
        entity_name=f"{row.employee_name} / {row.leave_type_name} / {row.year}",
        new_data={
            "employee_id": row.employee_id,
            "leave_type_id": row.leave_type_id,
            "year": row.year,
            "allocated_days": row.allocated_days,
            "carryover_days": row.carryover_days,
        },
        ip_address=ip, user_agent=ua,
    )
    await session.commit()
    return row


@router.get("/{ent_id}", response_model=LeaveEntitlementRead, summary="Chi tiết ngày phép")
async def get_entitlement(
    ent_id: int,
    _: User = require_permission("leaves:view"),
    session: AsyncSession = Depends(get_session),
):
    return await leave_entitlement_service.get_entitlement(session, ent_id)


@router.put("/{ent_id}", response_model=LeaveEntitlementRead, summary="Cập nhật ngày phép")
async def update_entitlement(
    ent_id: int,
    body: LeaveEntitlementUpdate,
    request: Request,
    current_user: User = require_permission("leaves:edit"),
    session: AsyncSession = Depends(get_session),
):
    row = await leave_entitlement_service.update_entitlement(session, ent_id, body)
    ip, ua = _meta(request)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="leave_entitlement", entity_id=ent_id,
        entity_name=f"{row.employee_name} / {row.leave_type_name} / {row.year}",
        new_data=body.model_dump(exclude_none=True),
        ip_address=ip, user_agent=ua,
    )
    await session.commit()
    return row


@router.delete("/{ent_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa ngày phép")
async def delete_entitlement(
    ent_id: int,
    request: Request,
    current_user: User = require_permission("leaves:delete"),
    session: AsyncSession = Depends(get_session),
):
    await leave_entitlement_service.delete_entitlement(session, ent_id)
    ip, ua = _meta(request)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="leave_entitlement", entity_id=ent_id,
        entity_name=str(ent_id),
        ip_address=ip, user_agent=ua,
    )
    await session.commit()
