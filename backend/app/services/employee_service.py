from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import hash_sensitive
from app.models.catalog import AdministrativeUnit
from app.models.employee import Employee, EmployeeAddress, EmployeeBankAccount
from app.models.employee_code import EmployeeCodeSequence
from app.models.employee_job import EmployeeJobRecord
from app.models.org import Department, JobPosition, JobTitle
from app.schemas.employee import (
    EmployeeAddressWrite,
    EmployeeBankAccountWrite,
    EmployeeCreate,
    EmployeeUpdate,
)
from app.services import (
    employee_code_service,
    employee_education_service,
    employee_insurance_service,
    employee_job_service,
    employee_relative_service,
)
from app.services.administrative_import_service import normalize_text


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _id_number_equals(value: str):
    return Employee.id_number_hash == hash_sensitive(value)


def compute_display_code(employee_seq: int, dept_display_prefix: Optional[str] = None) -> str:
    return employee_code_service.compute_employee_display_code(
        employee_seq,
        dept_display_prefix,
        min_digits=4,
    )


async def get_employee_by_id(session: AsyncSession, employee_id: int) -> Optional[Employee]:
    return await session.get(Employee, employee_id)


async def _require_department(session: AsyncSession, department_id: int) -> Department:
    department = await session.get(Department, department_id)
    if not department:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng ban")
    return department


async def _require_job_title(session: AsyncSession, job_title_id: int) -> JobTitle:
    job_title = await session.get(JobTitle, job_title_id)
    if not job_title:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chức danh")
    return job_title


async def _resolve_initial_job_context(session: AsyncSession, payload: EmployeeCreate) -> tuple[Department | None, JobTitle | None, JobPosition | None]:
    department = None
    job_title = None
    job_position = None

    if payload.initial_department_id is not None:
        department = await _require_department(session, payload.initial_department_id)

    if payload.initial_job_title_id is not None:
        job_title = await _require_job_title(session, payload.initial_job_title_id)

    if payload.initial_job_position_id is not None:
        job_position = await session.get(JobPosition, payload.initial_job_position_id)
        if not job_position:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy vị trí công việc")

        if department is None:
            department = await _require_department(session, job_position.department_id)
        elif job_position.department_id != department.id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Vị trí công việc không thuộc phòng ban đã chọn",
            )

        if job_position.job_title_id is not None:
            if job_title is None:
                job_title = await _require_job_title(session, job_position.job_title_id)
            elif job_position.job_title_id != job_title.id:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Vị trí công việc không khớp với chức danh đã chọn",
                )

    return department, job_title, job_position


async def _resolve_employee_code_sequence_id(
    session: AsyncSession,
    payload: EmployeeCreate,
    *,
    department: Department | None,
    job_position: JobPosition | None,
) -> int | None:
    if payload.employee_code_sequence_id is not None:
        sequence = await session.get(EmployeeCodeSequence, payload.employee_code_sequence_id)
        if not sequence or not sequence.is_active:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Hệ mã nhân viên không hợp lệ hoặc đã ngừng áp dụng",
            )
        return sequence.id

    if department is None and job_position is None:
        return None

    sequence = await employee_code_service.resolve_employee_code_sequence(
        session,
        department_id=department.id if department else None,
        job_position_id=job_position.id if job_position else None,
    )
    return sequence.id if sequence else None


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
    allowed_department_ids: Optional[Sequence[int]] = None,
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
                _id_number_equals(keyword.strip()),
                Employee.phone_number.ilike(f"%{keyword.strip()}%"),
            )
        )

    q = select(Employee)
    if allowed_department_ids is not None:
        q = q.join(
            EmployeeJobRecord,
            (EmployeeJobRecord.employee_id == Employee.id)
            & (EmployeeJobRecord.is_current == True),  # noqa: E712
        )
        if not allowed_department_ids:
            filters.append(false())
        else:
            filters.append(EmployeeJobRecord.department_id.in_(allowed_department_ids))
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
    allowed_department_ids: Optional[Sequence[int]] = None,
    limit: int = 20,
) -> list[Employee]:
    filters = [Employee.is_active]
    q = select(Employee)
    if allowed_department_ids is not None:
        q = q.join(
            EmployeeJobRecord,
            (EmployeeJobRecord.employee_id == Employee.id)
            & (EmployeeJobRecord.is_current == True),  # noqa: E712
        )
        if not allowed_department_ids:
            return []
        filters.append(EmployeeJobRecord.department_id.in_(allowed_department_ids))
    if keyword:
        kw = keyword.strip()
        norm = normalize_text(kw)
        numeric_id: Optional[int] = None
        if kw.isdigit():
            try:
                numeric_id = int(kw)
            except ValueError:
                pass
        id_conditions = []
        if numeric_id is not None:
            id_conditions = [Employee.id == numeric_id, Employee.employee_seq == numeric_id]
        filters.append(
            or_(
                Employee.normalized_name.contains(norm),
                _id_number_equals(kw),
                *id_conditions,
            )
        )
    q = q.where(*filters).order_by(Employee.employee_seq).limit(limit)
    return list((await session.execute(q)).scalars().all())


async def get_employee_lookup_context_map(
    session: AsyncSession,
    employee_ids: list[int],
) -> dict[int, dict[str, Optional[int | str]]]:
    if not employee_ids:
        return {}

    result = await session.execute(
        select(
            EmployeeJobRecord.employee_id.label("employee_id"),
            Department.id.label("current_department_id"),
            Department.name.label("current_department_name"),
            JobPosition.id.label("current_job_position_id"),
            JobPosition.name.label("current_job_position_name"),
            JobTitle.id.label("current_job_title_id"),
            JobTitle.name.label("current_job_title_name"),
        )
        .select_from(EmployeeJobRecord)
        .join(Department, Department.id == EmployeeJobRecord.department_id)
        .outerjoin(JobPosition, JobPosition.id == EmployeeJobRecord.job_position_id)
        .outerjoin(JobTitle, JobTitle.id == EmployeeJobRecord.job_title_id)
        .where(
            EmployeeJobRecord.employee_id.in_(employee_ids),
            EmployeeJobRecord.is_current.is_(True),
        )
    )

    return {
        row.employee_id: {
            "current_department_id": row.current_department_id,
            "current_department_name": row.current_department_name,
            "current_job_position_id": row.current_job_position_id,
            "current_job_position_name": row.current_job_position_name,
            "current_job_title_id": row.current_job_title_id,
            "current_job_title_name": row.current_job_title_name,
        }
        for row in result
    }


async def create_employee(session: AsyncSession, payload: EmployeeCreate) -> Employee:
    department, job_title, job_position = await _resolve_initial_job_context(session, payload)
    sequence_id = await _resolve_employee_code_sequence_id(
        session,
        payload,
        department=department,
        job_position=job_position,
    )
    if sequence_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Phải có ngữ cảnh công việc hiện hành hoặc hệ mã nhân viên explicit khi tạo nhân viên",
        )

    if payload.employee_seq is not None:
        existing = (await session.execute(
            select(Employee).where(
                Employee.employee_code_sequence_id == sequence_id,
                Employee.employee_seq == payload.employee_seq,
            )
        )).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail=f"Mã số nhân viên {payload.employee_seq} đã tồn tại trong hệ mã đã chọn",
            )
        seq = payload.employee_seq
        await employee_code_service.ensure_sequence_next_value_at_least(
            session,
            sequence_id=sequence_id,
            candidate_next_value=seq + 1,
        )
    else:
        seq = await employee_code_service.allocate_employee_seq(
            session,
            sequence_id=sequence_id,
        )

    # Kiểm tra trùng CCCD
    existing_id = (await session.execute(
        select(Employee).where(_id_number_equals(payload.id_number))
    )).scalar_one_or_none()
    if existing_id:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Số CCCD/CMND '{payload.id_number}' đã tồn tại",
        )

    normalized_bhxh_code = employee_insurance_service.normalize_bhxh_code(payload.bhxh_code)

    emp = Employee(
        employee_seq=seq,
        employee_code_sequence_id=sequence_id,
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
        id_number_hash=hash_sensitive(payload.id_number),
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
        bhxh_code=normalized_bhxh_code,
        status=payload.status,
        start_date=payload.start_date,
        resigned_date=payload.resigned_date,
        user_id=payload.user_id,
        is_active=True,
        created_at=_utcnow(),
    )
    session.add(emp)
    await session.flush()
    await employee_insurance_service.ensure_employee_insurance_profile(session, emp)

    if department is not None:
        effective_from = payload.initial_job_effective_from or payload.start_date
        session.add(
            EmployeeJobRecord(
                employee_id=emp.id,
                department_id=department.id,
                job_title_id=job_title.id if job_title else None,
                job_position_id=job_position.id if job_position else None,
                probation_start_date=payload.initial_probation_start_date,
                probation_end_date=payload.initial_probation_end_date,
                official_date=payload.initial_official_date,
                effective_from=effective_from,
                is_current=True,
                notes=payload.initial_job_notes,
                created_at=_utcnow(),
            )
        )
    return emp


async def update_employee(
    session: AsyncSession, employee_id: int, payload: EmployeeUpdate
) -> Employee:
    emp = await _get_or_404(session, employee_id)

    # Kiểm tra trùng CCCD nếu đổi số CCCD
    if payload.id_number and payload.id_number != emp.id_number:
        existing = (await session.execute(
            select(Employee).where(
                _id_number_equals(payload.id_number),
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
    if "id_number" in update_data:
        update_data["id_number_hash"] = hash_sensitive(update_data["id_number"])
    if "bhxh_code" in update_data:
        update_data["bhxh_code"] = employee_insurance_service.normalize_bhxh_code(update_data["bhxh_code"])

    for field, value in update_data.items():
        setattr(emp, field, value)
    if "bhxh_code" in update_data:
        await employee_insurance_service.sync_employee_profile_from_employee(session, emp)
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


def _compose_address_text_from_names(
    addr: EmployeeAddress,
    names: dict[int, str],
) -> str:
    explicit = (addr.full_address_text or "").strip()
    if explicit:
        return explicit

    new_parts = [
        (addr.new_address_line or "").strip(),
        names.get(addr.new_ward_unit_id, "") if addr.new_ward_unit_id else "",
        names.get(addr.new_province_unit_id, "") if addr.new_province_unit_id else "",
    ]
    new_text = ", ".join(part for part in new_parts if part)
    if new_text:
        return new_text

    old_parts = [
        (addr.old_address_line or "").strip(),
        names.get(addr.old_ward_unit_id, "") if addr.old_ward_unit_id else "",
        names.get(addr.old_district_unit_id, "") if addr.old_district_unit_id else "",
        names.get(addr.old_province_unit_id, "") if addr.old_province_unit_id else "",
    ]
    return ", ".join(part for part in old_parts if part)


async def compose_full_address_text(session: AsyncSession, addr: EmployeeAddress) -> str:
    ids: set[int] = set()
    for unit_id in (
        addr.old_province_unit_id,
        addr.old_district_unit_id,
        addr.old_ward_unit_id,
        addr.new_province_unit_id,
        addr.new_ward_unit_id,
    ):
        if unit_id:
            ids.add(unit_id)
    names = await _resolve_unit_names(session, ids)
    return _compose_address_text_from_names(addr, names)


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
        d["full_address_text"] = _compose_address_text_from_names(a, names) or None
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

    composed_addr = EmployeeAddress(**data)
    data["full_address_text"] = await compose_full_address_text(session, composed_addr) or None

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
    current_record = await employee_job_service.get_current_job_record(session, emp.id)
    current_job = await employee_job_service.build_job_record_read(session, current_record) if current_record else None
    relatives = await employee_relative_service.get_relatives(session, emp.id)
    education_histories = await employee_education_service.get_education_histories(session, emp.id)
    work_experiences = await employee_education_service.get_work_experiences(session, emp.id)
    skills = await employee_education_service.get_employee_skills(session, emp.id)
    certificates = await employee_education_service.get_employee_certificates(session, emp.id)
    languages = await employee_education_service.get_employee_languages(session, emp.id)
    return {
        "addresses": await enrich_addresses(session, addresses),
        "bank_accounts": bank_accounts,
        "display_code": await employee_code_service.build_employee_display_code(session, emp),
        "current_job": current_job,
        "relatives": relatives,
        "education_histories": education_histories,
        "work_experiences": work_experiences,
        "skills": skills,
        "certificates": certificates,
        "languages": languages,
    }
