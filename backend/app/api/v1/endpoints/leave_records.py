from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.leave_record import (
    CancelRequest,
    LeaveRecordCreate,
    LeaveRecordListPage,
    LeaveRecordRead,
    LeaveRecordUpdate,
)
from app.services import auth_service, leave_record_service
from datetime import date

router = APIRouter()


def _meta(request: Request) -> tuple[str | None, str | None]:
    return (
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )


@router.get("", response_model=LeaveRecordListPage, summary="Danh sách ghi nhận nghỉ phép")
async def list_records(
    employee_id:   Optional[int]  = Query(None),
    leave_type_id: Optional[int]  = Query(None),
    year:          Optional[int]  = Query(None),
    status_filter: Optional[str]  = Query(None, alias="status"),
    date_from:     Optional[date] = Query(None),
    date_to:       Optional[date] = Query(None),
    keyword:       Optional[str]  = Query(None),
    page:          int            = Query(1, ge=1),
    page_size:     int            = Query(20, ge=1, le=100),
    current_user: User = require_permission("leaves:read"),
    session: AsyncSession = Depends(get_session),
):
    result = await leave_record_service.list_records(
        session,
        employee_id=employee_id,
        leave_type_id=leave_type_id,
        year=year,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return result


@router.get("/{record_id}", response_model=LeaveRecordRead, summary="Chi tiết ghi nhận nghỉ phép")
async def get_record(
    record_id: int,
    current_user: User = require_permission("leaves:read"),
    session: AsyncSession = Depends(get_session),
):
    return await leave_record_service.get_record(session, record_id)


@router.post("", response_model=LeaveRecordRead, status_code=status.HTTP_201_CREATED, summary="Tạo ghi nhận nghỉ phép")
async def create_record(
    body: LeaveRecordCreate,
    request: Request,
    current_user: User = require_permission("leaves:create"),
    session: AsyncSession = Depends(get_session),
):
    result = await leave_record_service.create_record(session, body, current_user.id)
    await session.commit()
    ip, ua = _meta(request)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="leave_record", entity_id=result.id,
        entity_name=f"{result.employee_name} {result.start_date}–{result.end_date}",
        new_data={"total_days": result.total_days, "leave_type": result.leave_type_code},
        ip_address=ip, user_agent=ua,
    )
    return result


@router.put("/{record_id}", response_model=LeaveRecordRead, summary="Cập nhật ghi nhận nghỉ phép")
async def update_record(
    record_id: int,
    body: LeaveRecordUpdate,
    request: Request,
    current_user: User = require_permission("leaves:create"),
    session: AsyncSession = Depends(get_session),
):
    result = await leave_record_service.update_record(session, record_id, body)
    await session.commit()
    ip, ua = _meta(request)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="leave_record", entity_id=record_id,
        entity_name=f"leave_record/{record_id}",
        new_data=body.model_dump(exclude_none=True),
        ip_address=ip, user_agent=ua,
    )
    return result


@router.post("/{record_id}/cancel", response_model=LeaveRecordRead, summary="Hủy ghi nhận nghỉ phép")
async def cancel_record(
    record_id: int,
    body: CancelRequest,
    request: Request,
    current_user: User = require_permission("leaves:create"),
    session: AsyncSession = Depends(get_session),
):
    result = await leave_record_service.cancel_record(session, record_id, body)
    await session.commit()
    ip, ua = _meta(request)
    await auth_service.log_audit(
        session, current_user.id, "CANCEL",
        entity_type="leave_record", entity_id=record_id,
        entity_name=f"leave_record/{record_id}",
        new_data={"cancel_reason": body.cancel_reason},
        ip_address=ip, user_agent=ua,
    )
    return result


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa ghi nhận nghỉ phép")
async def delete_record(
    record_id: int,
    request: Request,
    current_user: User = require_permission("leaves:delete"),
    session: AsyncSession = Depends(get_session),
):
    await leave_record_service.delete_record(session, record_id)
    await session.commit()
    ip, ua = _meta(request)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="leave_record", entity_id=record_id,
        entity_name=f"leave_record/{record_id}",
        ip_address=ip, user_agent=ua,
    )
