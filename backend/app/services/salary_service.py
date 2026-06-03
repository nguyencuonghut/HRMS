from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import String, and_, func, or_, select
from sqlalchemy import cast as sa_cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import AuditLog, User
from app.models.employee import Employee
from app.models.employee_contract import EmployeeContract
from app.models.employee_insurance import EmployeeInsuranceProfile
from app.models.employee_job import EmployeeJobRecord
from app.models.employee_code import EmployeeCodeSequence
from app.models.insurance import (
    InsuranceChangeEvent,
    InsuranceContributionComponent,
    InsurancePolicyComponentRate,
    InsurancePolicyVersion,
)
from app.models.org import Department, JobPosition
from app.models.salary_adjustment import BhxhSalaryAdjustment
from app.schemas.salary import (
    BhxhSalaryAdjustmentCreate,
    BhxhSalaryAdjustmentListPage,
    BhxhSalaryAdjustmentRead,
    BhxhSalaryHistoryItem,
    SalaryBhxhBasisDetail,
    SalaryEmployeeListPage,
    SalaryEmployeeRow,
    SalarySummaryPage,
    SalarySummaryRates,
    SalarySummaryRow,
    SalarySummaryTotals,
)
from app.services import employee_code_service
from app.services.administrative_import_service import normalize_text
from app.services.insurance_change_service import (
    _compute_rate_totals,
    _compute_suggested_declaration,
    _load_active_policy,
    _load_current_contract,
    _load_ethnicity_bhxh_code,
    _load_nationality_code,
)


def _has_discrepancy(
    basis_amount: Optional[Decimal],
    basis_source: Optional[str],
    contract_salary: Optional[Decimal],
) -> bool:
    """Cảnh báo chỉ khi source=manual_fixed nhưng khác mức trong hợp đồng đang hiệu lực."""
    return (
        basis_source == "manual_fixed"
        and basis_amount is not None
        and contract_salary is not None
        and basis_amount != contract_salary
    )


async def _get_active_contract(
    session: AsyncSession, employee_id: int
) -> Optional[EmployeeContract]:
    row = (
        await session.execute(
            select(EmployeeContract)
            .where(
                EmployeeContract.employee_id == employee_id,
                EmployeeContract.status == "active",
                EmployeeContract.insurance_salary.is_not(None),
            )
            .order_by(EmployeeContract.effective_from.desc(), EmployeeContract.id.desc())
            .limit(1)
        )
    ).scalars().first()
    return row


async def list_salary_employees(
    session: AsyncSession,
    *,
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    participation_status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> SalaryEmployeeListPage:
    stmt = (
        select(
            Employee,
            EmployeeInsuranceProfile,
            Department.id.label("dept_id"),
            Department.name.label("department_name"),
            JobPosition.name.label("position_title"),
        )
        .outerjoin(EmployeeInsuranceProfile, EmployeeInsuranceProfile.employee_id == Employee.id)
        .outerjoin(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current.is_(True),
            ),
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
        .outerjoin(JobPosition, JobPosition.id == EmployeeJobRecord.job_position_id)
        .join(EmployeeCodeSequence, EmployeeCodeSequence.id == Employee.employee_code_sequence_id)
        .where(Employee.status != "resigned")
    )

    if search:
        kw_norm = f"%{normalize_text(search.strip())}%"
        kw_raw = f"%{search.strip()}%"
        generated_code = EmployeeCodeSequence.code + func.lpad(
            sa_cast(Employee.employee_seq, String),
            EmployeeCodeSequence.min_digits,
            "0",
        )
        stmt = stmt.where(
            or_(
                Employee.normalized_name.ilike(kw_norm),
                generated_code.ilike(kw_raw),
            )
        )

    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)

    if participation_status is not None:
        stmt = stmt.where(EmployeeInsuranceProfile.participation_status == participation_status)

    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    rows = (
        await session.execute(
            stmt.order_by(Employee.full_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    # Batch build employee codes
    emp_ids = [r.Employee.id for r in rows]
    emp_objects = [r.Employee for r in rows]
    code_map = await employee_code_service.batch_build_employee_display_codes(session, emp_objects)

    # Fetch active contracts for each employee in one query
    active_contracts: dict[int, EmployeeContract] = {}
    if emp_ids:
        # Subquery: most recent active contract per employee
        contract_rows = (
            await session.execute(
                select(EmployeeContract)
                .where(
                    EmployeeContract.employee_id.in_(emp_ids),
                    EmployeeContract.status == "active",
                    EmployeeContract.insurance_salary.is_not(None),
                )
                .order_by(
                    EmployeeContract.employee_id,
                    EmployeeContract.effective_from.desc(),
                )
            )
        ).scalars().all()
        # Keep only the first (newest) per employee
        for c in contract_rows:
            if c.employee_id not in active_contracts:
                active_contracts[c.employee_id] = c

    items = []
    for row in rows:
        emp: Employee = row.Employee
        profile: Optional[EmployeeInsuranceProfile] = row.EmployeeInsuranceProfile
        contract = active_contracts.get(emp.id)
        contract_salary = contract.insurance_salary if contract else None
        basis_source = profile.insurance_basis_source if profile else None
        raw_basis_amount = profile.insurance_basis_amount if profile else None
        # Khi source='contract', basis_amount lưu trong contract chứ không trong profile
        basis_amount = raw_basis_amount if raw_basis_amount is not None else (
            contract_salary if basis_source in {"contract", "computed"} else None
        )

        items.append(SalaryEmployeeRow(
            employee_id=emp.id,
            employee_code=code_map.get(emp.id, str(emp.employee_seq)),
            full_name=emp.full_name,
            department_id=row.dept_id,
            department_name=row.department_name,
            position_title=row.position_title,
            insurance_basis_amount=basis_amount,
            insurance_basis_source=basis_source,
            participation_status=profile.participation_status if profile else None,
            active_contract_insurance_salary=contract_salary,
            has_discrepancy=_has_discrepancy(basis_amount, basis_source, contract_salary),
        ))

    return SalaryEmployeeListPage(items=items, total=total, page=page, page_size=page_size)


async def get_employee_bhxh_basis(
    session: AsyncSession,
    employee_id: int,
) -> SalaryBhxhBasisDetail:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    profile = (
        await session.execute(
            select(EmployeeInsuranceProfile).where(
                EmployeeInsuranceProfile.employee_id == employee_id
            )
        )
    ).scalars().first()

    job_row = (
        await session.execute(
            select(EmployeeJobRecord, Department, JobPosition)
            .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
            .outerjoin(JobPosition, JobPosition.id == EmployeeJobRecord.job_position_id)
            .where(
                EmployeeJobRecord.employee_id == employee_id,
                EmployeeJobRecord.is_current.is_(True),
            )
        )
    ).first()

    dept_name: Optional[str] = None
    pos_title: Optional[str] = None
    if job_row:
        dept_name = job_row.Department.name if job_row.Department else None
        pos_title = job_row.JobPosition.name if job_row.JobPosition else None

    contract = await _get_active_contract(session, employee_id)

    basis_source = profile.insurance_basis_source if profile else None
    contract_salary = contract.insurance_salary if contract else None
    raw_basis_amount = profile.insurance_basis_amount if profile else None
    basis_amount = raw_basis_amount if raw_basis_amount is not None else (
        contract_salary if basis_source in {"contract", "computed"} else None
    )

    employee_code = await employee_code_service.build_employee_display_code(session, emp)

    contract_type: Optional[str] = None
    if contract:
        from app.models.catalog import ContractCategory
        cat = await session.get(ContractCategory, contract.contract_category_id)
        contract_type = cat.name if cat else None

    return SalaryBhxhBasisDetail(
        employee_id=emp.id,
        employee_code=employee_code,
        full_name=emp.full_name,
        department_name=dept_name,
        position_title=pos_title,
        insurance_basis_amount=basis_amount,
        insurance_basis_source=basis_source,
        participation_status=profile.participation_status if profile else None,
        active_contract_id=contract.id if contract else None,
        active_contract_type=contract_type,
        active_contract_insurance_salary=contract_salary,
        active_contract_effective_from=contract.effective_from if contract else None,
        has_discrepancy=_has_discrepancy(basis_amount, basis_source, contract_salary),
    )


async def get_employee_bhxh_history(
    session: AsyncSession,
    employee_id: int,
) -> list[BhxhSalaryHistoryItem]:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    items: list[BhxhSalaryHistoryItem] = []

    # Nguồn 1: contracts với insurance_salary
    from app.models.catalog import ContractCategory
    contract_rows = (
        await session.execute(
            select(EmployeeContract, ContractCategory)
            .outerjoin(ContractCategory, ContractCategory.id == EmployeeContract.contract_category_id)
            .where(
                EmployeeContract.employee_id == employee_id,
                EmployeeContract.insurance_salary.is_not(None),
            )
            .order_by(EmployeeContract.effective_from.desc())
            .limit(50)
        )
    ).all()

    for contract, cat in contract_rows:
        items.append(BhxhSalaryHistoryItem(
            effective_date=contract.effective_from,
            basis_amount=contract.insurance_salary,
            source_type="contract",
            note=cat.name if cat else None,
            decision_number=None,
            old_basis_amount=None,
            created_by_name=None,
        ))

    # Nguồn 2: BhxhSalaryAdjustment
    adj_rows = (
        await session.execute(
            select(BhxhSalaryAdjustment, User)
            .outerjoin(User, User.id == BhxhSalaryAdjustment.created_by_id)
            .where(BhxhSalaryAdjustment.employee_id == employee_id)
            .order_by(BhxhSalaryAdjustment.effective_date.desc())
            .limit(50)
        )
    ).all()
    for adj, creator in adj_rows:
        items.append(BhxhSalaryHistoryItem(
            effective_date=adj.effective_date,
            basis_amount=adj.new_basis_amount,
            source_type="manual_adjustment",
            note=adj.reason,
            decision_number=adj.decision_number,
            old_basis_amount=adj.old_basis_amount,
            created_by_name=creator.full_name if creator else None,
        ))

    # Sắp xếp theo effective_date giảm dần
    items.sort(key=lambda x: x.effective_date, reverse=True)
    return items


# ── Adjustment helpers ────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _build_adjustment_read(
    adj: BhxhSalaryAdjustment,
    employee_code: str,
    employee_name: str,
    department_name: Optional[str],
    created_by_name: Optional[str],
) -> BhxhSalaryAdjustmentRead:
    direction = "increase" if adj.new_basis_amount > adj.old_basis_amount else "decrease"
    change_amt = abs(adj.new_basis_amount - adj.old_basis_amount)
    change_pct = float(change_amt / adj.old_basis_amount * 100)
    return BhxhSalaryAdjustmentRead(
        id=adj.id,
        employee_id=adj.employee_id,
        employee_code=employee_code,
        employee_name=employee_name,
        department_name=department_name,
        decision_number=adj.decision_number,
        old_basis_amount=adj.old_basis_amount,
        new_basis_amount=adj.new_basis_amount,
        change_direction=direction,
        change_amount=change_amt,
        change_pct=round(change_pct, 2),
        effective_date=adj.effective_date,
        reason=adj.reason,
        created_by_id=adj.created_by_id,
        created_by_name=created_by_name,
        created_at=adj.created_at,
        insurance_change_event_id=adj.insurance_change_event_id,
    )


# ── create_bhxh_adjustment ────────────────────────────────────────────────────

async def create_bhxh_adjustment(
    session: AsyncSession,
    data: BhxhSalaryAdjustmentCreate,
    created_by_id: int,
) -> BhxhSalaryAdjustmentRead:
    # Bước 1: Validate
    employee = await session.get(Employee, data.employee_id)
    if not employee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy nhân viên")

    profile = (
        await session.execute(
            select(EmployeeInsuranceProfile).where(
                EmployeeInsuranceProfile.employee_id == data.employee_id
            )
        )
    ).scalars().first()
    if not profile:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Nhân viên chưa có hồ sơ bảo hiểm",
        )

    # Bước 2: Snapshot old_basis_amount
    contract = await _get_active_contract(session, data.employee_id)
    contract_salary = contract.insurance_salary if contract else None
    raw_basis = profile.insurance_basis_amount
    old_basis: Optional[Decimal] = raw_basis if raw_basis is not None else (
        contract_salary if profile.insurance_basis_source in {"contract", "computed"} else None
    )
    if old_basis is None or old_basis <= 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Không xác định được mức lương BHXH hiện tại — "
            "vui lòng cập nhật hợp đồng hoặc nhập mức cố định trước",
        )
    if old_basis == data.new_basis_amount:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Mức lương BHXH mới phải khác mức hiện tại",
        )

    # Bước 3: Tạo BhxhSalaryAdjustment
    adj = BhxhSalaryAdjustment(
        employee_id=data.employee_id,
        decision_number=data.decision_number,
        old_basis_amount=old_basis,
        new_basis_amount=data.new_basis_amount,
        effective_date=data.effective_date,
        reason=data.reason,
        created_by_id=created_by_id,
        created_at=_utcnow(),
    )
    session.add(adj)
    await session.flush()  # lấy adj.id

    # Bước 4: Tạo InsuranceChangeEvent
    is_increase = data.new_basis_amount > old_basis
    change_type = "increase" if is_increase else "decrease"
    ibhxh_code = "T-05" if is_increase else "G-07"

    nationality_code = await _load_nationality_code(session, employee.nationality_id)
    ethnicity_bhxh_code = await _load_ethnicity_bhxh_code(session, employee.ethnicity_id)
    now = _utcnow()
    sugg_year, sugg_month = _compute_suggested_declaration(data.effective_date, now)
    active_policy = await _load_active_policy(session)
    emp_rate_total = Decimal("0")
    er_rate_total = Decimal("0")
    policy_code: Optional[str] = None
    if active_policy:
        emp_rate_total, er_rate_total = await _compute_rate_totals(session, active_policy.id)
        policy_code = active_policy.code
    current_contract = await _load_current_contract(session, data.employee_id)
    contract_type_code: Optional[str] = None
    if current_contract and current_contract.document_kind:
        contract_type_code = current_contract.document_kind[:5]

    employee_code = await employee_code_service.build_employee_display_code(session, employee)

    event = InsuranceChangeEvent(
        employee_id=data.employee_id,
        change_type=change_type,
        change_reason="manual_correction",
        ibhxh_reason_code=ibhxh_code,
        effective_date=data.effective_date,
        period_year=data.effective_date.year,
        period_month=data.effective_date.month,
        employee_name_snapshot=employee.full_name,
        date_of_birth_snapshot=employee.date_of_birth,
        gender_snapshot=employee.gender,
        nationality_code_snapshot=nationality_code,
        identity_number_snapshot=employee.id_number,
        contract_number_snapshot=current_contract.contract_number if current_contract else None,
        contract_type_code_snapshot=contract_type_code,
        contract_signed_date_snapshot=current_contract.signed_date if current_contract else None,
        contract_from_snapshot=current_contract.effective_from if current_contract else None,
        contract_to_snapshot=current_contract.effective_to if current_contract else None,
        bhxh_code_snapshot=profile.bhxh_code,
        basis_amount=data.new_basis_amount,
        allowances_amount=Decimal("0"),
        bhyt_clinic_name_snapshot=profile.bhyt_initial_clinic_name,
        bhyt_clinic_code_snapshot=profile.bhyt_initial_clinic_code,
        policy_version_code_snapshot=policy_code,
        employee_rate_total_snapshot=emp_rate_total,
        employer_rate_total_snapshot=er_rate_total,
        ethnicity_bhxh_code_snapshot=ethnicity_bhxh_code,
        old_status=profile.participation_status,
        new_status=profile.participation_status or "active",
        suggested_declaration_year=sugg_year,
        suggested_declaration_month=sugg_month,
        is_manual=True,
        note=(
            f"Điều chỉnh lương BHXH: {int(old_basis):,} → {int(data.new_basis_amount):,} đ. "
            f"Lý do: {data.reason}"
        ),
        created_by_id=created_by_id,
        created_at=now,
    )
    session.add(event)
    await session.flush()

    # Bước 5: Cập nhật profile
    profile.insurance_basis_amount = data.new_basis_amount
    profile.insurance_basis_source = "manual_fixed"
    session.add(profile)

    # Bước 6: Link event vào adjustment
    adj.insurance_change_event_id = event.id
    session.add(adj)

    # Bước 7: AuditLog
    audit = AuditLog(
        user_id=created_by_id,
        action="bhxh_salary_adjustment_created",
        entity_type="employee",
        entity_id=data.employee_id,
        entity_name=employee.full_name,
        old_data={"basis_amount": str(old_basis)},
        new_data={
            "basis_amount": str(data.new_basis_amount),
            "adjustment_id": adj.id,
            "effective_date": str(data.effective_date),
        },
    )
    session.add(audit)
    await session.flush()

    # Bước 8: Commit (caller phải gọi session.commit())
    dept_name = None
    job_row = (
        await session.execute(
            select(EmployeeJobRecord, Department)
            .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
            .where(
                EmployeeJobRecord.employee_id == data.employee_id,
                EmployeeJobRecord.is_current.is_(True),
            )
        )
    ).first()
    if job_row:
        dept_name = job_row.Department.name if job_row.Department else None

    return _build_adjustment_read(adj, employee_code, employee.full_name, dept_name, None)


# ── list_adjustments ──────────────────────────────────────────────────────────

async def list_adjustments(
    session: AsyncSession,
    *,
    employee_id: Optional[int] = None,
    department_id: Optional[int] = None,
    search: Optional[str] = None,
    from_date=None,
    to_date=None,
    page: int = 1,
    page_size: int = 50,
) -> BhxhSalaryAdjustmentListPage:
    stmt = (
        select(BhxhSalaryAdjustment, Employee, User, Department)
        .join(Employee, Employee.id == BhxhSalaryAdjustment.employee_id)
        .outerjoin(User, User.id == BhxhSalaryAdjustment.created_by_id)
        .outerjoin(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current.is_(True),
            ),
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
        .join(EmployeeCodeSequence, EmployeeCodeSequence.id == Employee.employee_code_sequence_id)
    )
    if employee_id is not None:
        stmt = stmt.where(BhxhSalaryAdjustment.employee_id == employee_id)
    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)
    if from_date is not None:
        stmt = stmt.where(BhxhSalaryAdjustment.effective_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(BhxhSalaryAdjustment.effective_date <= to_date)
    if search:
        kw_norm = f"%{normalize_text(search.strip())}%"
        kw_raw = f"%{search.strip()}%"
        generated_code = EmployeeCodeSequence.code + func.lpad(
            sa_cast(Employee.employee_seq, String),
            EmployeeCodeSequence.min_digits,
            "0",
        )
        stmt = stmt.where(
            or_(
                Employee.normalized_name.ilike(kw_norm),
                generated_code.ilike(kw_raw),
            )
        )

    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    rows = (
        await session.execute(
            stmt.order_by(
                BhxhSalaryAdjustment.effective_date.desc(),
                BhxhSalaryAdjustment.created_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    emp_objects = [r.Employee for r in rows]
    code_map = await employee_code_service.batch_build_employee_display_codes(session, emp_objects)

    items = [
        _build_adjustment_read(
            r.BhxhSalaryAdjustment,
            code_map.get(r.Employee.id, str(r.Employee.employee_seq)),
            r.Employee.full_name,
            r.Department.name if r.Department else None,
            r.User.full_name if r.User else None,
        )
        for r in rows
    ]
    return BhxhSalaryAdjustmentListPage(items=items, total=total, page=page, page_size=page_size)


# ── get_employee_adjustment_history ──────────────────────────────────────────

async def get_employee_adjustment_history(
    session: AsyncSession,
    employee_id: int,
) -> list[BhxhSalaryAdjustmentRead]:
    emp = await session.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Không tìm thấy nhân viên")

    rows = (
        await session.execute(
            select(BhxhSalaryAdjustment, User)
            .outerjoin(User, User.id == BhxhSalaryAdjustment.created_by_id)
            .where(BhxhSalaryAdjustment.employee_id == employee_id)
            .order_by(BhxhSalaryAdjustment.effective_date.desc())
        )
    ).all()

    employee_code = await employee_code_service.build_employee_display_code(session, emp)

    job_row = (
        await session.execute(
            select(EmployeeJobRecord, Department)
            .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
            .where(
                EmployeeJobRecord.employee_id == employee_id,
                EmployeeJobRecord.is_current.is_(True),
            )
        )
    ).first()
    dept_name = job_row.Department.name if job_row and job_row.Department else None

    return [
        _build_adjustment_read(
            adj,
            employee_code,
            emp.full_name,
            dept_name,
            creator.full_name if creator else None,
        )
        for adj, creator in rows
    ]


# ── Salary summary helpers ────────────────────────────────────────────────────

async def _get_rates_for_month(
    session: AsyncSession,
    year: int,
    month: int,
) -> tuple[dict[str, dict], InsurancePolicyVersion]:
    """Trả rates grouped by insurance_kind và policy version dùng cho tháng."""
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    policy = (
        await session.execute(
            select(InsurancePolicyVersion)
            .where(
                InsurancePolicyVersion.effective_from <= last_day,
                or_(
                    InsurancePolicyVersion.effective_to.is_(None),
                    InsurancePolicyVersion.effective_to >= first_day,
                ),
            )
            .order_by(InsurancePolicyVersion.effective_from.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if not policy:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Chưa cấu hình tỷ lệ đóng BHXH cho tháng {month:02d}/{year}. "
            "Vào mục Cấu hình BHXH để thêm.",
        )

    rate_rows = (
        await session.execute(
            select(InsurancePolicyComponentRate, InsuranceContributionComponent)
            .join(
                InsuranceContributionComponent,
                InsuranceContributionComponent.code == InsurancePolicyComponentRate.component_code,
            )
            .where(
                InsurancePolicyComponentRate.policy_version_id == policy.id,
                InsurancePolicyComponentRate.is_active.is_(True),
            )
        )
    ).all()

    if not rate_rows:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Chưa cấu hình tỷ lệ đóng BHXH cho tháng {month:02d}/{year}. "
            "Vào mục Cấu hình BHXH để thêm.",
        )

    grouped: dict[str, dict] = {}
    for rate_row, comp in rate_rows:
        kind = comp.insurance_kind.upper()
        if kind not in grouped:
            grouped[kind] = {"employee_rate": Decimal("0"), "employer_rate": Decimal("0")}
        grouped[kind]["employee_rate"] += Decimal(str(rate_row.employee_rate_percent))
        grouped[kind]["employer_rate"] += Decimal(str(rate_row.employer_rate_percent))

    for key in ("BHXH", "BHYT", "BHTN"):
        grouped.setdefault(key, {"employee_rate": Decimal("0"), "employer_rate": Decimal("0")})

    return grouped, policy


def _compute_contributions(basis: Decimal, rates: dict[str, dict]) -> dict:
    def pct(r: Decimal) -> Decimal:
        return (basis * r / Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    bhxh_emp = pct(rates["BHXH"]["employee_rate"])
    bhyt_emp = pct(rates["BHYT"]["employee_rate"])
    bhtn_emp = pct(rates["BHTN"]["employee_rate"])
    total_emp = bhxh_emp + bhyt_emp + bhtn_emp

    bhxh_er = pct(rates["BHXH"]["employer_rate"])
    bhyt_er = pct(rates["BHYT"]["employer_rate"])
    bhtn_er = pct(rates["BHTN"]["employer_rate"])
    total_er = bhxh_er + bhyt_er + bhtn_er

    return {
        "bhxh_employee": bhxh_emp,
        "bhyt_employee": bhyt_emp,
        "bhtn_employee": bhtn_emp,
        "total_employee": total_emp,
        "bhxh_employer": bhxh_er,
        "bhyt_employer": bhyt_er,
        "bhtn_employer": bhtn_er,
        "total_employer": total_er,
        "grand_total": total_emp + total_er,
    }


def _build_summary_query(department_id: Optional[int]):
    """Base query cho summary — trả rows employee có basis xác định."""
    contract_sq = (
        select(
            EmployeeContract.employee_id.label("employee_id"),
            func.max(EmployeeContract.insurance_salary).label("insurance_salary"),
        )
        .where(
            EmployeeContract.status == "active",
            EmployeeContract.insurance_salary.is_not(None),
        )
        .group_by(EmployeeContract.employee_id)
        .subquery("active_contract")
    )

    stmt = (
        select(
            Employee,
            EmployeeInsuranceProfile,
            Department,
            EmployeeCodeSequence,
            contract_sq.c.insurance_salary.label("contract_salary"),
        )
        .join(EmployeeInsuranceProfile, EmployeeInsuranceProfile.employee_id == Employee.id)
        .outerjoin(
            EmployeeJobRecord,
            and_(
                EmployeeJobRecord.employee_id == Employee.id,
                EmployeeJobRecord.is_current.is_(True),
            ),
        )
        .outerjoin(Department, Department.id == EmployeeJobRecord.department_id)
        .join(EmployeeCodeSequence, EmployeeCodeSequence.id == Employee.employee_code_sequence_id)
        .outerjoin(contract_sq, contract_sq.c.employee_id == Employee.id)
        .where(
            EmployeeInsuranceProfile.participation_status == "active",
            Employee.status != "resigned",
            or_(
                EmployeeInsuranceProfile.insurance_basis_amount.is_not(None),
                and_(
                    EmployeeInsuranceProfile.insurance_basis_source.in_(("contract", "computed")),
                    contract_sq.c.insurance_salary.is_not(None),
                ),
            ),
        )
    )

    if department_id is not None:
        stmt = stmt.where(EmployeeJobRecord.department_id == department_id)

    stmt = stmt.order_by(
        Department.name.asc().nullslast(),
        Employee.employee_seq.asc(),
    )
    return stmt


def _resolve_basis_from_row(profile: EmployeeInsuranceProfile, contract_salary) -> Decimal:
    raw = profile.insurance_basis_amount
    if raw is not None:
        return Decimal(str(raw))
    return Decimal(str(contract_salary))


def _build_summary_row(stt: int, emp: Employee, profile: EmployeeInsuranceProfile,
                       dept: Optional[Department], seq: EmployeeCodeSequence,
                       contract_salary, rates: dict) -> SalarySummaryRow:
    emp_code = seq.code + str(emp.employee_seq).zfill(seq.min_digits)
    basis = _resolve_basis_from_row(profile, contract_salary)
    contrib = _compute_contributions(basis, rates)
    return SalarySummaryRow(
        stt=stt,
        employee_id=emp.id,
        employee_code=emp_code,
        full_name=emp.full_name,
        department_name=dept.name if dept else None,
        basis_amount=basis,
        **contrib,
    )


# ── get_salary_summary ────────────────────────────────────────────────────────

async def get_salary_summary(
    session: AsyncSession,
    *,
    year: int,
    month: int,
    department_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 100,
) -> SalarySummaryPage:
    rates, _ = await _get_rates_for_month(session, year, month)
    stmt = _build_summary_query(department_id)

    total = (
        await session.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()

    rows = (
        await session.execute(stmt.offset((page - 1) * page_size).limit(page_size))
    ).all()

    offset = (page - 1) * page_size
    items = [
        _build_summary_row(
            offset + i + 1,
            r.Employee,
            r.EmployeeInsuranceProfile,
            r.Department,
            r.EmployeeCodeSequence,
            r.contract_salary,
            rates,
        )
        for i, r in enumerate(rows)
    ]

    zero = Decimal("0")
    totals = SalarySummaryTotals(
        total_employees=total,
        sum_basis=sum((x.basis_amount for x in items), zero),
        sum_bhxh_employee=sum((x.bhxh_employee for x in items), zero),
        sum_bhyt_employee=sum((x.bhyt_employee for x in items), zero),
        sum_bhtn_employee=sum((x.bhtn_employee for x in items), zero),
        sum_total_employee=sum((x.total_employee for x in items), zero),
        sum_bhxh_employer=sum((x.bhxh_employer for x in items), zero),
        sum_bhyt_employer=sum((x.bhyt_employer for x in items), zero),
        sum_bhtn_employer=sum((x.bhtn_employer for x in items), zero),
        sum_total_employer=sum((x.total_employer for x in items), zero),
        sum_grand_total=sum((x.grand_total for x in items), zero),
    )

    summary_rates = SalarySummaryRates(
        bhxh_employee_rate=rates["BHXH"]["employee_rate"],
        bhyt_employee_rate=rates["BHYT"]["employee_rate"],
        bhtn_employee_rate=rates["BHTN"]["employee_rate"],
        bhxh_employer_rate=rates["BHXH"]["employer_rate"],
        bhyt_employer_rate=rates["BHYT"]["employer_rate"],
        bhtn_employer_rate=rates["BHTN"]["employer_rate"],
    )

    return SalarySummaryPage(
        year=year,
        month=month,
        rates=summary_rates,
        items=items,
        totals=totals,
        total=total,
        page=page,
        page_size=page_size,
    )


# ── get_salary_summary_all ────────────────────────────────────────────────────

async def get_salary_summary_all(
    session: AsyncSession,
    *,
    year: int,
    month: int,
    department_id: Optional[int] = None,
) -> tuple[list[SalarySummaryRow], SalarySummaryRates]:
    """Trả tất cả rows (không phân trang) dùng cho export."""
    rates, _ = await _get_rates_for_month(session, year, month)
    stmt = _build_summary_query(department_id)
    rows = (await session.execute(stmt)).all()

    items = [
        _build_summary_row(i + 1, r.Employee, r.EmployeeInsuranceProfile,
                           r.Department, r.EmployeeCodeSequence, r.contract_salary, rates)
        for i, r in enumerate(rows)
    ]

    summary_rates = SalarySummaryRates(
        bhxh_employee_rate=rates["BHXH"]["employee_rate"],
        bhyt_employee_rate=rates["BHYT"]["employee_rate"],
        bhtn_employee_rate=rates["BHTN"]["employee_rate"],
        bhxh_employer_rate=rates["BHXH"]["employer_rate"],
        bhyt_employer_rate=rates["BHYT"]["employer_rate"],
        bhtn_employer_rate=rates["BHTN"]["employer_rate"],
    )
    return items, summary_rates
