"""Service quản lý hợp đồng lao động nhân viên (4.1)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ContractCategory
from app.models.employee import Employee
from app.models.employee_contract import EmployeeContract
from app.schemas.employee_contract import (
    ContractCreate,
    ContractListPage,
    ContractRead,
    ContractUpdate,
    _days_until,
    _status_display,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_read(c: EmployeeContract, category_name: str, appendices: list[ContractRead] | None = None) -> ContractRead:
    return ContractRead(
        id=c.id,
        employee_id=c.employee_id,
        parent_contract_id=c.parent_contract_id,
        contract_category_id=c.contract_category_id,
        document_kind=c.document_kind,
        contract_number=c.contract_number,
        signed_date=c.signed_date,
        effective_from=c.effective_from,
        effective_to=c.effective_to,
        insurance_salary=c.insurance_salary,
        status=c.status,
        status_display=_status_display(c.status, c.effective_to),
        days_until_expiry=_days_until(c.status, c.effective_to),
        has_file=bool(c.file_path),
        file_name=c.file_name,
        file_size=c.file_size,
        mime_type=c.mime_type,
        category_name=category_name,
        notes=c.notes,
        created_at=c.created_at,
        updated_at=c.updated_at,
        appendices=appendices or [],
    )


async def _get_category_or_404(session: AsyncSession, category_id: int) -> ContractCategory:
    cat = await session.get(ContractCategory, category_id)
    if not cat or not cat.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy loại hợp đồng")
    return cat


async def _get_contract_or_404(session: AsyncSession, employee_id: int, contract_id: int) -> EmployeeContract:
    c = await session.get(EmployeeContract, contract_id)
    if not c or c.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hợp đồng")
    return c


async def _build_category_map(session: AsyncSession, contracts: list[EmployeeContract]) -> dict[int, str]:
    cat_ids = {c.contract_category_id for c in contracts}
    if not cat_ids:
        return {}
    rows = await session.execute(select(ContractCategory).where(ContractCategory.id.in_(cat_ids)))
    return {cat.id: cat.name for cat in rows.scalars().all()}


# ── Per-employee CRUD ─────────────────────────────────────────────────────────

async def get_contracts(session: AsyncSession, employee_id: int) -> list[ContractRead]:
    """Trả về danh sách HĐ gốc kèm phụ lục lồng vào nhau, sắp xếp theo ngày hiệu lực giảm dần."""
    rows = await session.execute(
        select(EmployeeContract)
        .where(EmployeeContract.employee_id == employee_id)
        .order_by(EmployeeContract.effective_from.desc(), EmployeeContract.id.desc())
    )
    all_contracts = list(rows.scalars().all())
    cat_map = await _build_category_map(session, all_contracts)

    # Phân nhóm: HĐ gốc và phụ lục
    appendix_map: dict[int, list[ContractRead]] = {}
    for c in all_contracts:
        if c.parent_contract_id is not None:
            appendix_map.setdefault(c.parent_contract_id, []).append(
                _to_read(c, cat_map.get(c.contract_category_id, ""))
            )

    result: list[ContractRead] = []
    for c in all_contracts:
        if c.parent_contract_id is None:
            result.append(_to_read(c, cat_map.get(c.contract_category_id, ""), appendix_map.get(c.id, [])))

    return result


async def get_contract_detail(session: AsyncSession, employee_id: int, contract_id: int) -> ContractRead:
    c = await _get_contract_or_404(session, employee_id, contract_id)
    cat = await session.get(ContractCategory, c.contract_category_id)
    cat_name = cat.name if cat else ""

    # Load phụ lục nếu là HĐ gốc
    appendices: list[ContractRead] = []
    if c.parent_contract_id is None:
        rows = await session.execute(
            select(EmployeeContract)
            .where(
                EmployeeContract.employee_id == employee_id,
                EmployeeContract.parent_contract_id == contract_id,
            )
            .order_by(EmployeeContract.effective_from.desc())
        )
        sub = list(rows.scalars().all())
        sub_cat_map = await _build_category_map(session, sub)
        appendices = [_to_read(s, sub_cat_map.get(s.contract_category_id, "")) for s in sub]

    return _to_read(c, cat_name, appendices)


async def create_contract(
    session: AsyncSession,
    employee_id: int,
    payload: ContractCreate,
    created_by: Optional[int] = None,
) -> ContractRead:
    # Kiểm tra nhân viên tồn tại
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    # Kiểm tra loại HĐ
    cat = await _get_category_or_404(session, payload.contract_category_id)

    # Kiểm tra parent nếu là phụ lục
    if payload.parent_contract_id is not None:
        parent = await session.get(EmployeeContract, payload.parent_contract_id)
        if not parent or parent.employee_id != employee_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="HĐ gốc không tồn tại hoặc không thuộc nhân viên này")
        if parent.status == "terminated":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Không thể thêm phụ lục vào hợp đồng đã hủy")

    # Kiểm tra số HĐ trùng
    dup = await session.execute(
        select(EmployeeContract).where(EmployeeContract.contract_number == payload.contract_number)
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Số hợp đồng '{payload.contract_number}' đã tồn tại")

    c = EmployeeContract(
        employee_id=employee_id,
        parent_contract_id=payload.parent_contract_id,
        contract_category_id=payload.contract_category_id,
        document_kind=cat.document_kind,
        contract_number=payload.contract_number,
        signed_date=payload.signed_date,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        insurance_salary=payload.insurance_salary,
        notes=payload.notes,
        status="active",
        created_by=created_by,
        created_at=_utcnow(),
    )
    session.add(c)
    await session.flush()
    await session.commit()
    await session.refresh(c)
    return _to_read(c, cat.name)


async def update_contract(
    session: AsyncSession,
    employee_id: int,
    contract_id: int,
    payload: ContractUpdate,
) -> ContractRead:
    c = await _get_contract_or_404(session, employee_id, contract_id)

    if c.status == "terminated":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Không thể sửa hợp đồng đã hủy")

    if payload.contract_number and payload.contract_number != c.contract_number:
        dup = await session.execute(
            select(EmployeeContract).where(EmployeeContract.contract_number == payload.contract_number)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Số hợp đồng '{payload.contract_number}' đã tồn tại")
        c.contract_number = payload.contract_number

    if payload.signed_date is not None:     c.signed_date     = payload.signed_date
    if payload.effective_from is not None:  c.effective_from  = payload.effective_from
    if payload.effective_to is not None:    c.effective_to    = payload.effective_to
    if payload.insurance_salary is not None: c.insurance_salary = payload.insurance_salary
    if payload.notes is not None:           c.notes           = payload.notes
    if payload.status == "terminated":      c.status          = "terminated"

    # Validate dates sau khi patch
    if c.effective_to and c.effective_to < c.effective_from:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="effective_to phải >= effective_from")

    c.updated_at = _utcnow()
    session.add(c)
    await session.commit()
    await session.refresh(c)

    cat = await session.get(ContractCategory, c.contract_category_id)
    return _to_read(c, cat.name if cat else "")


async def terminate_contract(session: AsyncSession, employee_id: int, contract_id: int) -> ContractRead:
    c = await _get_contract_or_404(session, employee_id, contract_id)
    if c.status == "terminated":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Hợp đồng đã ở trạng thái hủy")
    c.status = "terminated"
    c.updated_at = _utcnow()
    session.add(c)
    await session.commit()
    await session.refresh(c)
    cat = await session.get(ContractCategory, c.contract_category_id)
    return _to_read(c, cat.name if cat else "")


async def set_contract_file(
    session: AsyncSession,
    employee_id: int,
    contract_id: int,
    object_name: str,
    file_name: str,
    file_size: int,
    mime_type: Optional[str],
) -> ContractRead:
    c = await _get_contract_or_404(session, employee_id, contract_id)
    c.file_path  = object_name
    c.file_name  = file_name
    c.file_size  = file_size
    c.mime_type  = mime_type
    c.updated_at = _utcnow()
    session.add(c)
    await session.commit()
    await session.refresh(c)
    cat = await session.get(ContractCategory, c.contract_category_id)
    return _to_read(c, cat.name if cat else "")


async def remove_contract_file(
    session: AsyncSession,
    employee_id: int,
    contract_id: int,
) -> tuple[EmployeeContract, str]:
    """Trả về (contract, old_file_path) để caller xóa file trên MinIO."""
    c = await _get_contract_or_404(session, employee_id, contract_id)
    if not c.file_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Hợp đồng chưa có file đính kèm")
    old_path = c.file_path
    c.file_path  = None
    c.file_name  = None
    c.file_size  = None
    c.mime_type  = None
    c.updated_at = _utcnow()
    session.add(c)
    await session.commit()
    return c, old_path


# ── Global list ───────────────────────────────────────────────────────────────

async def list_contracts_global(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    employee_id: Optional[int] = None,
    document_kind: Optional[str] = None,
    status: Optional[str] = None,
    category_id: Optional[int] = None,
    expiring_within: Optional[int] = None,   # số ngày
    page: int = 1,
    page_size: int = 25,
) -> ContractListPage:
    from datetime import date, timedelta

    q = (
        select(EmployeeContract, ContractCategory, Employee)
        .join(ContractCategory, ContractCategory.id == EmployeeContract.contract_category_id)
        .join(Employee, Employee.id == EmployeeContract.employee_id)
    )

    if keyword:
        kw = f"%{keyword}%"
        q = q.where(
            EmployeeContract.contract_number.ilike(kw) |
            Employee.full_name.ilike(kw)
        )
    if employee_id:
        q = q.where(EmployeeContract.employee_id == employee_id)
    if document_kind:
        q = q.where(EmployeeContract.document_kind == document_kind)
    if status:
        q = q.where(EmployeeContract.status == status)
    if category_id:
        q = q.where(EmployeeContract.contract_category_id == category_id)
    if expiring_within is not None:
        today = date.today()
        deadline = today + timedelta(days=expiring_within)
        q = q.where(
            EmployeeContract.effective_to.isnot(None),
            EmployeeContract.effective_to >= today,
            EmployeeContract.effective_to <= deadline,
            EmployeeContract.status.in_(["active", "draft"]),
        )

    count_q = select(func.count()).select_from(q.subquery())
    total = (await session.execute(count_q)).scalar_one()

    q = q.order_by(EmployeeContract.effective_from.desc(), EmployeeContract.id.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)

    rows = (await session.execute(q)).fetchall()
    items = [_to_read(c, cat.name) for c, cat, _ in rows]

    return ContractListPage(items=items, total=total, page=page, page_size=page_size)
