from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import AdministrativeUnit
from app.models.employee import Employee, EmployeeAddress, EmployeeBankAccount
from app.schemas.employee import (
    EmployeeAddressWrite,
    EmployeeBankAccountWrite,
    EmployeeCreate,
    EmployeeUpdate,
)
from app.services import employee_job_service, employee_relative_service
from app.services.administrative_import_service import normalize_text


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def compute_display_code(employee_seq: int, dept_display_prefix: Optional[str] = None) -> str:
    seq_str = f"{employee_seq:04d}"
    return f"{dept_display_prefix}{seq_str}" if dept_display_prefix else seq_str


async def next_employee_seq(session: AsyncSession) -> int:
    """Lấy employee_seq tiếp theo: dùng subquery SELECT FOR UPDATE để tránh race condition."""
    result = await session.execute(
        select(Employee.employee_seq)
        .order_by(Employee.employee_seq.desc())
        .limit(1)
        .with_for_update()
    )
    current_max = result.scalar()
    return (current_max or 0) + 1


async def get_employee_by_id(session: AsyncSession, employee_id: int) -> Optional[Employee]:
    return await session.get(Employee, employee_id)


async def _get_or_404(session: AsyncSession, employee_id: int) -> Employee:
    emp = await get_employee_by_id(session, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    return emp


async def list_employees_page(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    filters = []
    if is_active is not None:
        filters.append(Employee.is_active == is_active)
    if status:
        filters.append(Employee.status == status)
    if keyword:
        norm = normalize_text(keyword)
        filters.append(
            or_(
                Employee.normalized_name.contains(norm),
                Employee.id_number.ilike(f"%{keyword.strip()}%"),
                Employee.phone_number.ilike(f"%{keyword.strip()}%"),
            )
        )

    q = select(Employee)
    if filters:
        q = q.where(*filters)

    total_q = select(func.count()).select_from(q.subquery())
    total = (await session.execute(total_q)).scalar_one()

    offset = (page - 1) * page_size
    rows = (await session.execute(
        q.order_by(Employee.employee_seq).offset(offset).limit(page_size)
    )).scalars().all()

    return {"items": list(rows), "total": total, "page": page, "page_size": page_size}


async def lookup_employees(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    limit: int = 20,
) -> list[Employee]:
    filters = [Employee.is_active == True]
    if keyword:
        norm = normalize_text(keyword)
        filters.append(
            or_(
                Employee.normalized_name.contains(norm),
                Employee.id_number.ilike(f"%{keyword.strip()}%"),
            )
        )
    q = select(Employee).where(*filters).order_by(Employee.employee_seq).limit(limit)
    return list((await session.execute(q)).scalars().all())


async def create_employee(session: AsyncSession, payload: EmployeeCreate) -> Employee:
    if payload.employee_seq is not None:
        existing = (await session.execute(
            select(Employee).where(Employee.employee_seq == payload.employee_seq)
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"Mã số nhân viên {payload.employee_seq} đã tồn tại",
            )
        seq = payload.employee_seq
    else:
        seq = await next_employee_seq(session)

    # Kiểm tra trùng CCCD
    existing_id = (await session.execute(
        select(Employee).where(Employee.id_number == payload.id_number)
    )).scalar_one_or_none()
    if existing_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Số CCCD/CMND '{payload.id_number}' đã tồn tại",
        )

    emp = Employee(
        employee_seq=seq,
        full_name=payload.full_name,
        normalized_name=normalize_text(payload.full_name),
        last_name=payload.last_name,
        first_name=payload.first_name,
        date_of_birth=payload.date_of_birth,
        gender=payload.gender,
        nationality_id=payload.nationality_id,
        ethnicity_id=payload.ethnicity_id,
        religion_id=payload.religion_id,
        id_number=payload.id_number,
        id_issued_on=payload.id_issued_on,
        id_issued_by=payload.id_issued_by,
        id_expires_on=payload.id_expires_on,
        passport_number=payload.passport_number,
        passport_issued_on=payload.passport_issued_on,
        passport_expires_on=payload.passport_expires_on,
        work_permit_number=payload.work_permit_number,
        work_permit_issued_on=payload.work_permit_issued_on,
        work_permit_expires_on=payload.work_permit_expires_on,
        phone_number=payload.phone_number,
        personal_email=payload.personal_email,
        personal_tax_code=payload.personal_tax_code,
        bhxh_code=payload.bhxh_code,
        status=payload.status,
        start_date=payload.start_date,
        resigned_date=payload.resigned_date,
        user_id=payload.user_id,
        is_active=True,
        created_at=_utcnow(),
    )
    session.add(emp)
    return emp


async def update_employee(
    session: AsyncSession, employee_id: int, payload: EmployeeUpdate
) -> Employee:
    emp = await _get_or_404(session, employee_id)

    # Kiểm tra trùng CCCD nếu đổi số CCCD
    if payload.id_number and payload.id_number != emp.id_number:
        existing = (await session.execute(
            select(Employee).where(
                Employee.id_number == payload.id_number,
                Employee.id != employee_id,
            )
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"Số CCCD/CMND '{payload.id_number}' đã tồn tại",
            )

    update_data = payload.model_dump(exclude_unset=True)
    if "full_name" in update_data:
        update_data["normalized_name"] = normalize_text(update_data["full_name"])

    for field, value in update_data.items():
        setattr(emp, field, value)
    emp.updated_at = _utcnow()
    return emp


async def soft_delete_employee(session: AsyncSession, employee_id: int) -> Employee:
    emp = await _get_or_404(session, employee_id)
    emp.is_active = False
    emp.updated_at = _utcnow()
    return emp


# ── Addresses ──────────────────────────────────────────────────────────────────

async def _resolve_unit_names(session: AsyncSession, unit_ids: set[int]) -> dict[int, str]:
    if not unit_ids:
        return {}
    rows = (await session.execute(
        select(AdministrativeUnit.id, AdministrativeUnit.name)
        .where(AdministrativeUnit.id.in_(unit_ids))
    )).all()
    return {row.id: row.name for row in rows}


async def enrich_addresses(session: AsyncSession, addresses: list[EmployeeAddress]) -> list[dict]:
    ids: set[int] = set()
    for a in addresses:
        for v in (a.old_province_unit_id, a.old_district_unit_id, a.old_ward_unit_id,
                  a.new_province_unit_id, a.new_ward_unit_id):
            if v:
                ids.add(v)
    names = await _resolve_unit_names(session, ids)
    result = []
    for a in addresses:
        d = a.model_dump()
        d["old_province_name"] = names.get(a.old_province_unit_id) if a.old_province_unit_id else None
        d["old_district_name"] = names.get(a.old_district_unit_id) if a.old_district_unit_id else None
        d["old_ward_name"] = names.get(a.old_ward_unit_id) if a.old_ward_unit_id else None
        d["new_province_name"] = names.get(a.new_province_unit_id) if a.new_province_unit_id else None
        d["new_ward_name"] = names.get(a.new_ward_unit_id) if a.new_ward_unit_id else None
        result.append(d)
    return result


async def build_address_read(session: AsyncSession, addr: EmployeeAddress) -> dict:
    enriched = await enrich_addresses(session, [addr])
    return enriched[0]


async def get_employee_addresses(
    session: AsyncSession, employee_id: int
) -> list[EmployeeAddress]:
    rows = (await session.execute(
        select(EmployeeAddress).where(EmployeeAddress.employee_id == employee_id)
    )).scalars().all()
    return list(rows)


async def upsert_employee_address(
    session: AsyncSession, employee_id: int, payload: EmployeeAddressWrite
) -> EmployeeAddress:
    await _get_or_404(session, employee_id)
    existing = (await session.execute(
        select(EmployeeAddress).where(
            EmployeeAddress.employee_id == employee_id,
            EmployeeAddress.address_type == payload.address_type,
        )
    )).scalar_one_or_none()

    data = payload.model_dump()
    data["employee_id"] = employee_id

    if existing:
        for field, value in data.items():
            setattr(existing, field, value)
        existing.updated_at = _utcnow()
        return existing

    addr = EmployeeAddress(**data, created_at=_utcnow())
    session.add(addr)
    return addr


# ── Bank Accounts ──────────────────────────────────────────────────────────────

async def get_employee_bank_accounts(
    session: AsyncSession, employee_id: int
) -> list[EmployeeBankAccount]:
    rows = (await session.execute(
        select(EmployeeBankAccount).where(EmployeeBankAccount.employee_id == employee_id)
    )).scalars().all()
    return list(rows)


async def create_bank_account(
    session: AsyncSession, employee_id: int, payload: EmployeeBankAccountWrite
) -> EmployeeBankAccount:
    await _get_or_404(session, employee_id)

    if payload.is_primary:
        # Bỏ is_primary của tất cả tài khoản cũ
        existing_accounts = await get_employee_bank_accounts(session, employee_id)
        for acc in existing_accounts:
            if acc.is_primary:
                acc.is_primary = False
                acc.updated_at = _utcnow()

    account = EmployeeBankAccount(
        employee_id=employee_id,
        bank_id=payload.bank_id,
        account_number=payload.account_number,
        account_name=payload.account_name,
        branch_name=payload.branch_name,
        is_primary=payload.is_primary,
        note=payload.note,
        created_at=_utcnow(),
    )
    session.add(account)
    return account


async def update_bank_account(
    session: AsyncSession,
    employee_id: int,
    account_id: int,
    payload: EmployeeBankAccountWrite,
) -> EmployeeBankAccount:
    acc = await session.get(EmployeeBankAccount, account_id)
    if not acc or acc.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài khoản ngân hàng")

    if payload.is_primary and not acc.is_primary:
        existing_accounts = await get_employee_bank_accounts(session, employee_id)
        for other in existing_accounts:
            if other.is_primary and other.id != account_id:
                other.is_primary = False
                other.updated_at = _utcnow()

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(acc, field, value)
    acc.updated_at = _utcnow()
    return acc


async def delete_bank_account(
    session: AsyncSession, employee_id: int, account_id: int
) -> None:
    acc = await session.get(EmployeeBankAccount, account_id)
    if not acc or acc.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tài khoản ngân hàng")
    await session.delete(acc)


# ── Build EmployeeRead helpers ─────────────────────────────────────────────────

async def build_employee_read_data(
    session: AsyncSession, emp: Employee
) -> dict:
    """Trả về dict chứa tất cả data cần để build EmployeeRead."""
    addresses = await get_employee_addresses(session, emp.id)
    bank_accounts = await get_employee_bank_accounts(session, emp.id)
    prefix = await employee_job_service.get_display_code_prefix(session, emp.id)
    current_record = await employee_job_service.get_current_job_record(session, emp.id)
    current_job = await employee_job_service.build_job_record_read(session, current_record) if current_record else None
    relatives = await employee_relative_service.get_relatives(session, emp.id)
    return {
        "addresses": await enrich_addresses(session, addresses),
        "bank_accounts": bank_accounts,
        "display_code": compute_display_code(emp.employee_seq, prefix),
        "current_job": current_job,
        "relatives": relatives,
    }
