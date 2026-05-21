"""Service xử lý biến động tăng/giảm BHXH (Plan 6.3)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Ethnicity, Nationality
from app.models.employee import Employee
from app.models.employee_contract import EmployeeContract
from app.models.employee_insurance import EmployeeInsuranceProfile
from app.models.insurance import (
    InsuranceChangeEvent,
    InsurancePolicyComponentRate,
    InsurancePolicyVersion,
)
from app.schemas.insurance_change import (
    InsuranceChangeEventCreate,
    InsuranceChangeEventListPage,
    InsuranceChangeEventRead,
    InsuranceMonthlyChangeSummary,
)

# Mapping trạng thái cũ/mới → (change_type, change_reason, ibhxh_reason_code)
# Theo QĐ 595/QĐ-BHXH Phụ lục II
_STATUS_TRANSITION_MAP: dict[
    tuple[Optional[str], str], tuple[str, str, str]
] = {
    (None, "active"):       ("increase", "new_hire",          "T-01"),
    ("active", "paused"):   ("decrease", "unpaid_leave",      "G-03"),
    ("paused", "active"):   ("increase", "return_from_leave", "T-02"),
    ("active", "stopped"):  ("decrease", "resignation",       "G-01"),
    ("paused", "stopped"):  ("decrease", "contract_end",      "G-01"),
    ("stopped", "active"):  ("increase", "return_from_leave", "T-02"),
}

# Mapping change_reason → ibhxh_reason_code cho manual events
_MANUAL_REASON_MAP: dict[str, tuple[str, str]] = {
    "new_hire":                  ("increase", "T-01"),
    "return_from_leave":         ("increase", "T-02"),
    "transfer_in":               ("increase", "T-04"),
    "contract_renewal":          ("increase", "T-03"),
    "resignation":               ("decrease", "G-01"),
    "contract_end":              ("decrease", "G-01"),
    "dismissal":                 ("decrease", "G-02"),
    "unpaid_leave":              ("decrease", "G-03"),
    "maternity_no_contribution": ("decrease", "G-04"),
    "long_term_sick":            ("decrease", "G-05"),
    "transfer_out":              ("decrease", "G-06"),
    "manual_correction":         ("increase", "T-05"),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _compute_suggested_declaration(effective_date: date, created_at: datetime) -> tuple[int, int]:
    if effective_date.day <= 5:
        prev_month = effective_date.month - 1 if effective_date.month > 1 else 12
        prev_year = effective_date.year if effective_date.month > 1 else effective_date.year - 1
        if created_at.year == prev_year and created_at.month == prev_month:
            return prev_year, prev_month
    return effective_date.year, effective_date.month


async def _load_ethnicity_bhxh_code(
    session: AsyncSession, ethnicity_id: Optional[int]
) -> Optional[str]:
    if not ethnicity_id:
        return None
    eth = await session.get(Ethnicity, ethnicity_id)
    return eth.bhxh_code if eth else None


async def _load_nationality_code(session: AsyncSession, nationality_id: int) -> str:
    nat = await session.get(Nationality, nationality_id)
    if nat and nat.iso2_code:
        return nat.iso2_code
    if nat and nat.code:
        return nat.code[:10]
    return "VN"


async def _load_current_contract(
    session: AsyncSession, employee_id: int
) -> Optional[EmployeeContract]:
    row = await session.execute(
        select(EmployeeContract)
        .where(
            EmployeeContract.employee_id == employee_id,
            EmployeeContract.status == "active",
        )
        .order_by(EmployeeContract.effective_from.desc())
        .limit(1)
    )
    return row.scalar_one_or_none()


async def _load_active_policy(session: AsyncSession) -> Optional[InsurancePolicyVersion]:
    row = await session.execute(
        select(InsurancePolicyVersion).where(InsurancePolicyVersion.is_active.is_(True))
    )
    return row.scalar_one_or_none()


async def _compute_rate_totals(
    session: AsyncSession, policy_id: int
) -> tuple[Decimal, Decimal]:
    rows = await session.execute(
        select(InsurancePolicyComponentRate).where(
            InsurancePolicyComponentRate.policy_version_id == policy_id,
            InsurancePolicyComponentRate.is_active.is_(True),
        )
    )
    rates = list(rows.scalars().all())
    emp_total = sum(Decimal(str(r.employee_rate_percent)) for r in rates)
    er_total = sum(Decimal(str(r.employer_rate_percent)) for r in rates)
    return emp_total, er_total


def _resolve_basis_amount(
    profile: EmployeeInsuranceProfile,
    contract: Optional[EmployeeContract],
) -> Optional[Decimal]:
    if profile.insurance_basis_source == "manual_fixed" and profile.insurance_basis_amount:
        return profile.insurance_basis_amount
    if contract and contract.insurance_salary is not None:
        return Decimal(str(contract.insurance_salary))
    return None


async def record_status_change(
    session: AsyncSession,
    employee_id: int,
    old_status: Optional[str],
    new_status: str,
    profile: EmployeeInsuranceProfile,
    effective_date: date,
    created_by_id: Optional[int] = None,
) -> Optional[InsuranceChangeEvent]:
    transition = _STATUS_TRANSITION_MAP.get((old_status, new_status))
    if transition is None:
        return None

    change_type, change_reason, ibhxh_reason_code = transition

    employee = await session.get(Employee, employee_id)
    if not employee:
        return None

    nationality_code = await _load_nationality_code(session, employee.nationality_id)
    ethnicity_bhxh_code = await _load_ethnicity_bhxh_code(session, employee.ethnicity_id)
    contract = await _load_current_contract(session, employee_id)

    basis_amount = _resolve_basis_amount(profile, contract)
    if basis_amount is None or basis_amount <= 0:
        return None

    active_policy = await _load_active_policy(session)
    emp_rate_total = Decimal("0")
    er_rate_total = Decimal("0")
    policy_code: Optional[str] = None
    if active_policy:
        emp_rate_total, er_rate_total = await _compute_rate_totals(session, active_policy.id)
        policy_code = active_policy.code

    now = _utcnow()
    sugg_year, sugg_month = _compute_suggested_declaration(effective_date, now)

    contract_type_code: Optional[str] = None
    if contract and contract.document_kind:
        contract_type_code = contract.document_kind[:5]

    event = InsuranceChangeEvent(
        employee_id=employee_id,
        change_type=change_type,
        change_reason=change_reason,
        ibhxh_reason_code=ibhxh_reason_code,
        effective_date=effective_date,
        period_year=effective_date.year,
        period_month=effective_date.month,
        employee_name_snapshot=employee.full_name,
        date_of_birth_snapshot=employee.date_of_birth,
        gender_snapshot=employee.gender,
        nationality_code_snapshot=nationality_code,
        identity_number_snapshot=employee.id_number,
        contract_number_snapshot=contract.contract_number if contract else None,
        contract_type_code_snapshot=contract_type_code,
        contract_signed_date_snapshot=contract.signed_date if contract else None,
        contract_from_snapshot=contract.effective_from if contract else None,
        contract_to_snapshot=contract.effective_to if contract else None,
        bhxh_code_snapshot=profile.bhxh_code,
        basis_amount=basis_amount,
        allowances_amount=Decimal("0"),
        bhyt_clinic_name_snapshot=profile.bhyt_initial_clinic_name,
        bhyt_clinic_code_snapshot=profile.bhyt_initial_clinic_code,
        policy_version_code_snapshot=policy_code,
        employee_rate_total_snapshot=emp_rate_total,
        employer_rate_total_snapshot=er_rate_total,
        ethnicity_bhxh_code_snapshot=ethnicity_bhxh_code,
        old_status=old_status,
        new_status=new_status,
        suggested_declaration_year=sugg_year,
        suggested_declaration_month=sugg_month,
        is_manual=False,
        created_by_id=created_by_id,
        created_at=now,
    )
    session.add(event)
    await session.flush()
    return event


async def create_manual_event(
    session: AsyncSession,
    payload: InsuranceChangeEventCreate,
    created_by_id: Optional[int] = None,
) -> InsuranceChangeEvent:
    employee = await session.get(Employee, payload.employee_id)
    if not employee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    profile_row = await session.execute(
        select(EmployeeInsuranceProfile).where(
            EmployeeInsuranceProfile.employee_id == payload.employee_id
        )
    )
    profile = profile_row.scalar_one_or_none()
    if not profile:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Nhân viên chưa có hồ sơ bảo hiểm",
        )

    reason_map = _MANUAL_REASON_MAP.get(payload.change_reason)
    if reason_map is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"change_reason không hợp lệ: {payload.change_reason}",
        )
    _resolved_type, ibhxh_code = reason_map
    if _resolved_type != payload.change_type:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"change_reason '{payload.change_reason}' phải đi với "
                f"change_type='{_resolved_type}', không phải '{payload.change_type}'"
            ),
        )

    nationality_code = await _load_nationality_code(session, employee.nationality_id)
    ethnicity_bhxh_code = await _load_ethnicity_bhxh_code(session, employee.ethnicity_id)
    contract = await _load_current_contract(session, payload.employee_id)

    basis_amount = _resolve_basis_amount(profile, contract)
    if basis_amount is None or basis_amount <= 0:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Không xác định được mức đóng BHXH (basis_amount). "
                   "Vui lòng cập nhật hợp đồng hoặc nhập thủ công.",
        )

    active_policy = await _load_active_policy(session)
    emp_rate_total = Decimal("0")
    er_rate_total = Decimal("0")
    policy_code: Optional[str] = None
    if active_policy:
        emp_rate_total, er_rate_total = await _compute_rate_totals(session, active_policy.id)
        policy_code = active_policy.code

    now = _utcnow()
    sugg_year, sugg_month = _compute_suggested_declaration(payload.effective_date, now)

    contract_type_code: Optional[str] = None
    if contract and contract.document_kind:
        contract_type_code = contract.document_kind[:5]

    event = InsuranceChangeEvent(
        employee_id=payload.employee_id,
        change_type=payload.change_type,
        change_reason=payload.change_reason,
        ibhxh_reason_code=ibhxh_code,
        effective_date=payload.effective_date,
        period_year=payload.effective_date.year,
        period_month=payload.effective_date.month,
        employee_name_snapshot=employee.full_name,
        date_of_birth_snapshot=employee.date_of_birth,
        gender_snapshot=employee.gender,
        nationality_code_snapshot=nationality_code,
        identity_number_snapshot=employee.id_number,
        contract_number_snapshot=contract.contract_number if contract else None,
        contract_type_code_snapshot=contract_type_code,
        contract_signed_date_snapshot=contract.signed_date if contract else None,
        contract_from_snapshot=contract.effective_from if contract else None,
        contract_to_snapshot=contract.effective_to if contract else None,
        bhxh_code_snapshot=profile.bhxh_code,
        basis_amount=basis_amount,
        allowances_amount=Decimal("0"),
        bhyt_clinic_name_snapshot=profile.bhyt_initial_clinic_name,
        bhyt_clinic_code_snapshot=profile.bhyt_initial_clinic_code,
        policy_version_code_snapshot=policy_code,
        employee_rate_total_snapshot=emp_rate_total,
        employer_rate_total_snapshot=er_rate_total,
        ethnicity_bhxh_code_snapshot=ethnicity_bhxh_code,
        old_status=None,
        new_status=profile.participation_status,
        suggested_declaration_year=sugg_year,
        suggested_declaration_month=sugg_month,
        is_manual=True,
        note=payload.note,
        created_by_id=created_by_id,
        created_at=now,
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return event


async def list_change_events(
    session: AsyncSession,
    *,
    employee_id: Optional[int] = None,
    change_type: Optional[str] = None,
    period_year: Optional[int] = None,
    period_month: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
) -> InsuranceChangeEventListPage:
    stmt = select(InsuranceChangeEvent)

    if employee_id is not None:
        stmt = stmt.where(InsuranceChangeEvent.employee_id == employee_id)
    if change_type is not None:
        stmt = stmt.where(InsuranceChangeEvent.change_type == change_type)
    if period_year is not None:
        stmt = stmt.where(InsuranceChangeEvent.period_year == period_year)
    if period_month is not None:
        stmt = stmt.where(InsuranceChangeEvent.period_month == period_month)

    count_result = await session.execute(
        select(func.count()).select_from(stmt.subquery())
    )
    total = count_result.scalar_one()

    rows = await session.execute(
        stmt.order_by(
            InsuranceChangeEvent.period_year.desc(),
            InsuranceChangeEvent.period_month.desc(),
            InsuranceChangeEvent.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    events = list(rows.scalars().all())

    return InsuranceChangeEventListPage(
        items=[InsuranceChangeEventRead.model_validate(e, from_attributes=True) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


async def get_monthly_summary(
    session: AsyncSession,
    year: int,
    month: int,
) -> InsuranceMonthlyChangeSummary:
    rows = await session.execute(
        select(InsuranceChangeEvent).where(
            InsuranceChangeEvent.period_year == year,
            InsuranceChangeEvent.period_month == month,
        )
    )
    events = list(rows.scalars().all())

    increases = [e for e in events if e.change_type == "increase"]
    decreases = [e for e in events if e.change_type == "decrease"]

    return InsuranceMonthlyChangeSummary(
        period_year=year,
        period_month=month,
        increase_count=len(increases),
        decrease_count=len(decreases),
        total_basis_increase=sum((e.basis_amount for e in increases), Decimal("0")),
        total_basis_decrease=sum((e.basis_amount for e in decreases), Decimal("0")),
    )


async def delete_manual_event(session: AsyncSession, event_id: int) -> None:
    event = await session.get(InsuranceChangeEvent, event_id)
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy biến động")
    if not event.is_manual:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ được xóa biến động thủ công (is_manual=true)",
        )
    await session.delete(event)
    await session.commit()
