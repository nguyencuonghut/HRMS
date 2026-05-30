from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import LeaveType
from app.models.employee import Employee
from app.models.leave_entitlement import LeaveEntitlement
from app.models.leave_record import LeaveRecord
from app.schemas.leave_record import (
    CancelRequest,
    LeaveRecordCreate,
    LeaveRecordRead,
    LeaveRecordUpdate,
    compute_total_days,
)
from app.services import employee_code_service
from app.schemas.leave_entitlement import LeaveEntitlementRead


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _compute_remaining(ent: LeaveEntitlement) -> float:
    allocated = float(ent.allocated_days)
    carryover = float(ent.carryover_days)
    used = float(ent.used_days)
    if ent.carryover_expires and date.today() > ent.carryover_expires:
        used_from_regular = max(0.0, used - carryover)
        return allocated - used_from_regular
    return allocated + carryover - used


def _make_read(
    record: LeaveRecord,
    emp: Optional[Employee],
    lt: Optional[LeaveType],
    employee_code: str = "",
    warning: Optional[str] = None,
    remaining_days_after: Optional[float] = None,
) -> LeaveRecordRead:
    """Tạo LeaveRecordRead từ object đã load sẵn — KHÔNG hit DB."""
    return LeaveRecordRead(
        id=record.id,
        employee_id=record.employee_id,
        employee_code=employee_code,
        employee_name=emp.full_name if emp else "",
        leave_type_id=record.leave_type_id,
        leave_type_code=lt.code if lt else "",
        leave_type_name=lt.name if lt else "",
        entitlement_id=record.entitlement_id,
        start_date=record.start_date,
        end_date=record.end_date,
        start_half=record.start_half,
        end_half=record.end_half,
        total_days=float(record.total_days),
        reason=record.reason,
        status=record.status,
        cancel_reason=record.cancel_reason,
        note=record.note,
        created_by_id=record.created_by_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
        remaining_days_after=remaining_days_after,
        warning=warning,
    )


async def _build_read(
    session: AsyncSession,
    record: LeaveRecord,
    warning: Optional[str] = None,
    remaining_days_after: Optional[float] = None,
    employee_code: Optional[str] = None,
) -> LeaveRecordRead:
    """Dùng cho single-record ops (create/update/get). Với list dùng _make_read."""
    emp = await session.get(Employee, record.employee_id)
    lt = await session.get(LeaveType, record.leave_type_id)
    code = employee_code or (
        await employee_code_service.build_employee_display_code(session, emp) if emp else ""
    )
    return _make_read(record, emp, lt, code, warning, remaining_days_after)


async def _get_record_or_404(session: AsyncSession, record_id: int) -> LeaveRecord:
    row = await session.get(LeaveRecord, record_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi nghỉ phép")
    return row


async def _find_entitlement(
    session: AsyncSession,
    employee_id: int,
    leave_type_id: int,
    year: int,
) -> Optional[LeaveEntitlement]:
    return (await session.execute(
        select(LeaveEntitlement).where(
            LeaveEntitlement.employee_id == employee_id,
            LeaveEntitlement.leave_type_id == leave_type_id,
            LeaveEntitlement.year == year,
        )
    )).scalar_one_or_none()


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def list_records(
    session: AsyncSession,
    *,
    employee_id: Optional[int] = None,
    leave_type_id: Optional[int] = None,
    year: Optional[int] = None,
    status_filter: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    base = (
        select(LeaveRecord)
        .join(Employee, LeaveRecord.employee_id == Employee.id)
    )
    filters = []
    if employee_id is not None:
        filters.append(LeaveRecord.employee_id == employee_id)
    if leave_type_id is not None:
        filters.append(LeaveRecord.leave_type_id == leave_type_id)
    if year is not None:
        filters.append(func.extract("year", LeaveRecord.start_date) == year)
    if status_filter is not None:
        filters.append(LeaveRecord.status == status_filter)
    if date_from is not None:
        filters.append(LeaveRecord.end_date >= date_from)
    if date_to is not None:
        filters.append(LeaveRecord.start_date <= date_to)
    if keyword:
        kw = f"%{keyword.strip()}%"
        filters.append(Employee.full_name.ilike(kw))
    if filters:
        base = base.where(*filters)

    count_stmt = select(func.count()).select_from(
        select(LeaveRecord.id)
        .join(Employee, LeaveRecord.employee_id == Employee.id)
        .where(*filters)
        .subquery()
    )
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = (
        base
        .order_by(LeaveRecord.start_date.desc(), LeaveRecord.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(stmt)).scalars().all()

    # Batch load Employee + LeaveType — tránh N+1
    employee_ids  = {r.employee_id  for r in rows}
    leave_type_ids = {r.leave_type_id for r in rows}

    emp_map: dict[int, Employee] = {}
    lt_map:  dict[int, LeaveType] = {}

    if employee_ids:
        emps = (await session.execute(
            select(Employee).where(Employee.id.in_(employee_ids))
        )).scalars().all()
        emp_map = {e.id: e for e in emps}

    if leave_type_ids:
        lts = (await session.execute(
            select(LeaveType).where(LeaveType.id.in_(leave_type_ids))
        )).scalars().all()
        lt_map = {lt.id: lt for lt in lts}

    code_map = await employee_code_service.batch_build_employee_display_codes(
        session, list(emp_map.values())
    )

    items = [
        _make_read(
            r,
            emp_map.get(r.employee_id),
            lt_map.get(r.leave_type_id),
            employee_code=code_map.get(r.employee_id, ""),
        )
        for r in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def get_record(session: AsyncSession, record_id: int) -> LeaveRecordRead:
    row = await _get_record_or_404(session, record_id)
    return await _build_read(session, row)


async def create_record(
    session: AsyncSession,
    data: LeaveRecordCreate,
    created_by_id: int,
) -> LeaveRecordRead:
    lt = await session.get(LeaveType, data.leave_type_id)
    if not lt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy loại nghỉ phép")
    if not await session.get(Employee, data.employee_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    if (data.start_half or data.end_half) and not lt.allow_half_day:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Loại phép '{lt.name}' không hỗ trợ nghỉ nửa ngày",
        )

    total = compute_total_days(data.start_date, data.end_date, data.start_half, data.end_half)

    ent = await _find_entitlement(session, data.employee_id, data.leave_type_id, data.start_date.year)
    warning: Optional[str] = None
    remaining_after: Optional[float] = None

    if ent:
        ent.used_days += total
        ent.updated_at = _utcnow()
        remaining_after = _compute_remaining(ent)
        if remaining_after < 0:
            warning = f"Vượt phép {abs(remaining_after):.1f} ngày — số ngày còn lại: {remaining_after:.1f}"
        session.add(ent)
    else:
        warning = f"Chưa có phân bổ ngày phép {lt.name} năm {data.start_date.year} — không cập nhật used_days"

    record = LeaveRecord(
        employee_id=data.employee_id,
        leave_type_id=data.leave_type_id,
        entitlement_id=ent.id if ent else None,
        start_date=data.start_date,
        end_date=data.end_date,
        start_half=data.start_half,
        end_half=data.end_half,
        total_days=total,
        reason=data.reason,
        note=data.note,
        status="active",
        created_by_id=created_by_id,
        created_at=_utcnow(),
    )
    session.add(record)
    await session.flush()
    await session.refresh(record)
    return await _build_read(session, record, warning=warning, remaining_days_after=remaining_after)


async def update_record(
    session: AsyncSession,
    record_id: int,
    data: LeaveRecordUpdate,
) -> LeaveRecordRead:
    record = await _get_record_or_404(session, record_id)
    if record.status == "cancelled":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Không thể cập nhật bản ghi đã hủy")

    old_total = record.total_days

    new_start = data.start_date if data.start_date is not None else record.start_date
    new_end   = data.end_date   if data.end_date   is not None else record.end_date
    new_start_half = data.start_half if data.start_half is not None else record.start_half
    new_end_half   = data.end_half   if data.end_half   is not None else record.end_half

    if new_start > new_end:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="start_date phải ≤ end_date")
    if new_start.year != new_end.year:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Không hỗ trợ ghi nhận nghỉ phép vắt qua năm — vui lòng tạo 2 bản ghi",
        )

    lt = await session.get(LeaveType, record.leave_type_id)
    if (new_start_half or new_end_half) and lt and not lt.allow_half_day:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Loại phép '{lt.name}' không hỗ trợ nghỉ nửa ngày",
        )

    new_total = compute_total_days(new_start, new_end, new_start_half, new_end_half)
    delta = new_total - old_total

    if record.entitlement_id and delta != 0:
        ent = await session.get(LeaveEntitlement, record.entitlement_id)
        if ent:
            ent.used_days = max(Decimal("0"), ent.used_days + delta)
            ent.updated_at = _utcnow()
            session.add(ent)

    record.start_date  = new_start
    record.end_date    = new_end
    record.start_half  = new_start_half
    record.end_half    = new_end_half
    record.total_days  = new_total
    if data.reason is not None:
        record.reason = data.reason
    if data.note is not None:
        record.note = data.note
    record.updated_at = _utcnow()
    session.add(record)
    await session.flush()
    return await _build_read(session, record)


async def cancel_record(
    session: AsyncSession,
    record_id: int,
    data: CancelRequest,
) -> LeaveRecordRead:
    record = await _get_record_or_404(session, record_id)
    if record.status == "cancelled":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Bản ghi đã bị hủy")

    if record.entitlement_id:
        ent = await session.get(LeaveEntitlement, record.entitlement_id)
        if ent:
            ent.used_days = max(Decimal("0"), ent.used_days - record.total_days)
            ent.updated_at = _utcnow()
            session.add(ent)

    record.status = "cancelled"
    record.cancel_reason = data.cancel_reason
    record.updated_at = _utcnow()
    session.add(record)
    await session.flush()
    return await _build_read(session, record)


async def delete_record(session: AsyncSession, record_id: int) -> None:
    record = await _get_record_or_404(session, record_id)

    if record.entitlement_id and record.status == "active":
        ent = await session.get(LeaveEntitlement, record.entitlement_id)
        if ent:
            ent.used_days = max(Decimal("0"), ent.used_days - record.total_days)
            ent.updated_at = _utcnow()
            session.add(ent)

    await session.delete(record)
    await session.flush()
