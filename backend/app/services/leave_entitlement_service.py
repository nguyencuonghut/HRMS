from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import LeaveType
from app.models.employee import Employee
from app.models.leave_entitlement import LeaveEntitlement
from app.schemas.leave_entitlement import (
    BulkAllocateRequest,
    BulkAllocateResult,
    LeaveEntitlementCreate,
    LeaveEntitlementRead,
    LeaveEntitlementUpdate,
)
from app.services import employee_code_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_read(
    ent: LeaveEntitlement,
    emp: Employee,
    lt: LeaveType,
    *,
    employee_code: str,
) -> LeaveEntitlementRead:
    return LeaveEntitlementRead(
        id=ent.id,
        employee_id=ent.employee_id,
        employee_code=employee_code,
        employee_name=emp.full_name,
        leave_type_id=ent.leave_type_id,
        leave_type_code=lt.code,
        leave_type_name=lt.name,
        year=ent.year,
        allocated_days=float(ent.allocated_days),
        carryover_days=float(ent.carryover_days),
        carryover_expires=ent.carryover_expires,
        used_days=float(ent.used_days),
        note=ent.note,
        created_by_id=ent.created_by_id,
        created_at=ent.created_at,
        updated_at=ent.updated_at,
    )


def _seniority_bonus(start_date: date, alloc_year: int) -> int:
    """Tính số ngày thâm niên theo BLĐ 2019 Điều 114: cứ đủ 5 năm +1 ngày."""
    jan1 = date(alloc_year, 1, 1)
    years = alloc_year - start_date.year
    try:
        anniversary = start_date.replace(year=alloc_year)
    except ValueError:
        # 29/02 trên năm không nhuận
        anniversary = date(alloc_year, 3, 1)
    if jan1 < anniversary:
        years -= 1
    return max(0, years) // 5


def _compute_carryover(
    prev_ent: Optional[LeaveEntitlement],
    lt: LeaveType,
    alloc_year: int,
) -> tuple[Decimal, Optional[date]]:
    """
    Tính (carryover_days, carryover_expires) cho năm alloc_year dựa trên
    entitlement năm trước. FIFO: phép dư tiêu trước phép năm hiện tại.
    """
    if not lt.carryover_allowed or prev_ent is None:
        return Decimal("0"), None

    allocated = float(prev_ent.allocated_days)
    carryover = float(prev_ent.carryover_days)
    used = float(prev_ent.used_days)
    prev_expires = prev_ent.carryover_expires

    if prev_expires and date.today() > prev_expires:
        # FIFO sau cutoff: chỉ phần dùng vượt carryover mới trừ vào allocated
        used_from_regular = max(0.0, used - carryover)
        remaining_prev = allocated - used_from_regular
    else:
        remaining_prev = allocated + carryover - used

    carry = Decimal(str(max(0.0, remaining_prev))).quantize(Decimal("0.1"))

    _, last_day = calendar.monthrange(alloc_year, lt.carryover_cutoff_month)
    expires = date(alloc_year, lt.carryover_cutoff_month, last_day)

    return carry, expires


async def _get_ent_or_404(session: AsyncSession, ent_id: int) -> LeaveEntitlement:
    row = await session.get(LeaveEntitlement, ent_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi ngày phép")
    return row


async def _joined_read(session: AsyncSession, ent_id: int) -> LeaveEntitlementRead:
    stmt = (
        select(LeaveEntitlement, Employee, LeaveType)
        .join(Employee, LeaveEntitlement.employee_id == Employee.id)
        .join(LeaveType, LeaveEntitlement.leave_type_id == LeaveType.id)
        .where(LeaveEntitlement.id == ent_id)
    )
    row = (await session.execute(stmt)).one_or_none()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi ngày phép")
    ent, emp, lt = row
    return _build_read(
        ent,
        emp,
        lt,
        employee_code=await employee_code_service.build_employee_display_code(session, emp),
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

async def list_entitlements(
    session: AsyncSession,
    *,
    employee_id: Optional[int] = None,
    year: Optional[int] = None,
    leave_type_id: Optional[int] = None,
    department_id: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    base = (
        select(LeaveEntitlement, Employee, LeaveType)
        .join(Employee, LeaveEntitlement.employee_id == Employee.id)
        .join(LeaveType, LeaveEntitlement.leave_type_id == LeaveType.id)
    )
    filters = []
    if employee_id is not None:
        filters.append(LeaveEntitlement.employee_id == employee_id)
    if year is not None:
        filters.append(LeaveEntitlement.year == year)
    if leave_type_id is not None:
        filters.append(LeaveEntitlement.leave_type_id == leave_type_id)
    if keyword:
        kw = f"%{keyword.strip()}%"
        filters.append(Employee.full_name.ilike(kw))
    if filters:
        base = base.where(*filters)

    count_stmt = select(func.count()).select_from(
        select(LeaveEntitlement.id)
        .join(Employee, LeaveEntitlement.employee_id == Employee.id)
        .join(LeaveType, LeaveEntitlement.leave_type_id == LeaveType.id)
        .where(*filters)
        .subquery()
    )
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = (
        base
        .order_by(Employee.employee_seq, LeaveType.code, LeaveEntitlement.year.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(stmt)).all()
    employees = [emp for _, emp, _ in rows]
    code_map = await employee_code_service.batch_build_employee_display_codes(session, employees)
    items = [
        _build_read(ent, emp, lt, employee_code=code_map[emp.id])
        for ent, emp, lt in rows
    ]
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def get_entitlement(session: AsyncSession, ent_id: int) -> LeaveEntitlementRead:
    return await _joined_read(session, ent_id)


async def create_entitlement(
    session: AsyncSession,
    data: LeaveEntitlementCreate,
    created_by_id: int,
) -> LeaveEntitlementRead:
    # Kiểm tra employee và leave_type tồn tại
    if not await session.get(Employee, data.employee_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    if not await session.get(LeaveType, data.leave_type_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy loại nghỉ phép")

    # Kiểm tra trùng
    dup = (await session.execute(
        select(LeaveEntitlement).where(
            LeaveEntitlement.employee_id == data.employee_id,
            LeaveEntitlement.leave_type_id == data.leave_type_id,
            LeaveEntitlement.year == data.year,
        )
    )).scalar_one_or_none()
    if dup:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Đã tồn tại bản ghi ngày phép cho nhân viên này, loại phép này, năm {data.year}",
        )

    row = LeaveEntitlement(
        employee_id=data.employee_id,
        leave_type_id=data.leave_type_id,
        year=data.year,
        allocated_days=Decimal(str(data.allocated_days)),
        carryover_days=Decimal(str(data.carryover_days)),
        carryover_expires=data.carryover_expires,
        used_days=Decimal("0"),
        note=data.note,
        created_by_id=created_by_id,
        created_at=_utcnow(),
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return await _joined_read(session, row.id)


async def update_entitlement(
    session: AsyncSession,
    ent_id: int,
    data: LeaveEntitlementUpdate,
) -> LeaveEntitlementRead:
    row = await _get_ent_or_404(session, ent_id)
    if data.allocated_days is not None:
        row.allocated_days = Decimal(str(data.allocated_days))
    if data.carryover_days is not None:
        row.carryover_days = Decimal(str(data.carryover_days))
    if data.carryover_expires is not None:
        row.carryover_expires = data.carryover_expires
    if data.note is not None:
        row.note = data.note
    row.updated_at = _utcnow()
    session.add(row)
    await session.flush()
    return await _joined_read(session, ent_id)


async def delete_entitlement(session: AsyncSession, ent_id: int) -> None:
    row = await _get_ent_or_404(session, ent_id)
    if float(row.used_days) > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Không thể xóa: bản ghi đã có {float(row.used_days)} ngày đã sử dụng",
        )
    await session.delete(row)
    await session.flush()


# ── Bulk allocate ─────────────────────────────────────────────────────────────

async def bulk_allocate(
    session: AsyncSession,
    req: BulkAllocateRequest,
    created_by_id: int,
) -> BulkAllocateResult:
    lt_codes = req.leave_type_codes or ["annual_leave"]
    lt_rows = list((await session.execute(
        select(LeaveType).where(LeaveType.code.in_(lt_codes), LeaveType.is_active == True)
    )).scalars().all())

    unknown = set(lt_codes) - {lt.code for lt in lt_rows}
    if unknown:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Không tìm thấy hoặc đã vô hiệu hóa loại phép: {', '.join(sorted(unknown))}",
        )

    emp_stmt = select(Employee).where(Employee.is_active == True, Employee.status != "resigned")
    if req.employee_ids:
        emp_stmt = emp_stmt.where(Employee.id.in_(req.employee_ids))
    employees = list((await session.execute(emp_stmt)).scalars().all())

    now = _utcnow()
    allocated_count = 0
    skipped_count = 0
    errors: list[str] = []

    for emp in employees:
        for lt in lt_rows:
            # Tính số ngày cấp
            if lt.code == "annual_leave":
                alloc_days = Decimal(str(12 + _seniority_bonus(emp.start_date, req.year)))
            elif lt.max_days_per_year is not None:
                alloc_days = Decimal(str(lt.max_days_per_year))
            else:
                # Loại không có giới hạn và không phải annual_leave → bỏ qua
                continue

            # Tính carryover từ năm trước
            prev_ent: Optional[LeaveEntitlement] = None
            if lt.carryover_allowed:
                prev_ent = (await session.execute(
                    select(LeaveEntitlement).where(
                        LeaveEntitlement.employee_id == emp.id,
                        LeaveEntitlement.leave_type_id == lt.id,
                        LeaveEntitlement.year == req.year - 1,
                    )
                )).scalar_one_or_none()

            carry_days, carry_expires = _compute_carryover(prev_ent, lt, req.year)

            # Kiểm tra bản ghi đã tồn tại
            existing: Optional[LeaveEntitlement] = (await session.execute(
                select(LeaveEntitlement).where(
                    LeaveEntitlement.employee_id == emp.id,
                    LeaveEntitlement.leave_type_id == lt.id,
                    LeaveEntitlement.year == req.year,
                )
            )).scalar_one_or_none()

            if existing:
                if not req.overwrite and float(existing.used_days) > 0:
                    skipped_count += 1
                    continue
                existing.allocated_days = alloc_days
                existing.carryover_days = carry_days
                existing.carryover_expires = carry_expires
                existing.updated_at = now
                session.add(existing)
            else:
                session.add(LeaveEntitlement(
                    employee_id=emp.id,
                    leave_type_id=lt.id,
                    year=req.year,
                    allocated_days=alloc_days,
                    carryover_days=carry_days,
                    carryover_expires=carry_expires,
                    used_days=Decimal("0"),
                    created_by_id=created_by_id,
                    created_at=now,
                ))
            allocated_count += 1

    await session.commit()
    return BulkAllocateResult(
        year=req.year,
        allocated=allocated_count,
        skipped=skipped_count,
        errors=errors,
    )
