from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.employee_contract import EmployeeContract
from app.models.employee_insurance import (
    EmployeeInsuranceComponentOverride,
    EmployeeInsuranceProfile,
)
from app.models.employee_job import EmployeeJobRecord
from app.models.employee_relative import EmployeeRelative
from app.models.insurance import (
    InsuranceContributionComponent,
    InsurancePolicyComponentRate,
    InsurancePolicyVersion,
)
from app.models.org import Department, JobTitle
from app.schemas.employee_insurance import (
    EmployeeInsuranceListItem,
    EmployeeInsuranceListPage,
    EmployeeInsuranceProfileRead,
    EmployeeInsuranceProfileUpdate,
    InsuranceContributionComponentSnapshot,
)
from app.services import employee_code_service, insurance_change_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def normalize_bhxh_code(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def normalize_optional_insurance_code(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def derive_participation_status(employee_status: str) -> str:
    return "stopped" if employee_status == "resigned" else "active"


# ── Resolve helpers ────────────────────────────────────────────────────────────

def _resolve_basis_amount(
    profile: EmployeeInsuranceProfile,
    current_contract: Optional[EmployeeContract],
) -> tuple[Optional[Decimal], str]:
    if profile.insurance_basis_source == "manual_fixed":
        return profile.insurance_basis_amount, "manual_fixed"
    if profile.insurance_basis_source in {"contract", "computed"}:
        if profile.insurance_basis_amount is not None:
            return profile.insurance_basis_amount, profile.insurance_basis_source
        if current_contract and current_contract.insurance_salary is not None:
            return Decimal(str(current_contract.insurance_salary)), profile.insurance_basis_source
    return None, profile.insurance_basis_source


def _compute_contributions(
    basis_amount: Optional[Decimal],
    components: list[InsuranceContributionComponent],
    policy_rates: dict[str, InsurancePolicyComponentRate],
    overrides: dict[str, EmployeeInsuranceComponentOverride],
) -> list[InsuranceContributionComponentSnapshot]:
    results: list[InsuranceContributionComponentSnapshot] = []
    sorted_components = sorted(components, key=lambda c: (c.sort_order, c.code))
    for component in sorted_components:
        rate = policy_rates.get(component.code)
        if not rate:
            continue
        override = overrides.get(component.code)

        if override and not override.use_company_default:
            calc_mode = "fixed_amount"
            emp_amount = override.fixed_employee_amount
            erp_amount = override.fixed_employer_amount
            emp_rate = None
            erp_rate = None
            advances = (
                override.employer_advances_employee_part
                if override.employer_advances_employee_part is not None
                else rate.employer_advances_employee_part
            )
        else:
            calc_mode = "company_policy"
            emp_rate = Decimal(str(rate.employee_rate_percent))
            erp_rate = Decimal(str(rate.employer_rate_percent))
            if basis_amount is not None:
                emp_amount = (basis_amount * emp_rate / 100).quantize(Decimal("1"))
                erp_amount = (basis_amount * erp_rate / 100).quantize(Decimal("1"))
            else:
                emp_amount = None
                erp_amount = None
            advances = (
                override.employer_advances_employee_part
                if (override and override.employer_advances_employee_part is not None)
                else rate.employer_advances_employee_part
            )

        results.append(
            InsuranceContributionComponentSnapshot(
                component_code=component.code,
                component_name=component.name_vi,
                insurance_kind=component.insurance_kind,
                sort_order=component.sort_order,
                calc_mode=calc_mode,
                employee_rate_percent=emp_rate,
                employer_rate_percent=erp_rate,
                fixed_employee_amount=override.fixed_employee_amount if (override and not override.use_company_default) else None,
                fixed_employer_amount=override.fixed_employer_amount if (override and not override.use_company_default) else None,
                employer_advances_employee_part=advances,
                employee_amount=emp_amount,
                employer_amount=erp_amount,
            )
        )
    return results


async def _get_active_policy(session: AsyncSession) -> Optional[InsurancePolicyVersion]:
    row = await session.execute(
        select(InsurancePolicyVersion).where(InsurancePolicyVersion.is_active.is_(True))
    )
    return row.scalar_one_or_none()


async def _get_policy_rates(
    session: AsyncSession,
    policy_id: int,
) -> dict[str, InsurancePolicyComponentRate]:
    rows = await session.execute(
        select(InsurancePolicyComponentRate).where(
            InsurancePolicyComponentRate.policy_version_id == policy_id
        )
    )
    return {r.component_code: r for r in rows.scalars().all()}


async def _get_components(session: AsyncSession) -> list[InsuranceContributionComponent]:
    rows = await session.execute(
        select(InsuranceContributionComponent).where(
            InsuranceContributionComponent.is_active.is_(True)
        )
    )
    return list(rows.scalars().all())


async def _resolve_profile_policy(
    session: AsyncSession,
    profile: EmployeeInsuranceProfile,
    active_policy: Optional[InsurancePolicyVersion],
) -> Optional[InsurancePolicyVersion]:
    if profile.insurance_policy_version_id:
        return await session.get(InsurancePolicyVersion, profile.insurance_policy_version_id)
    return active_policy


async def _build_list_item(
    employee: Employee,
    employee_code: str,
    profile: Optional[EmployeeInsuranceProfile],
    department_name: Optional[str],
    job_title_name: Optional[str],
    current_contract: Optional[EmployeeContract],
    components: list[InsuranceContributionComponent],
    policy: Optional[InsurancePolicyVersion],
    policy_rates: dict[str, InsurancePolicyComponentRate],
    overrides: dict[str, EmployeeInsuranceComponentOverride],
) -> EmployeeInsuranceListItem:
    if not profile:
        return EmployeeInsuranceListItem(
            employee_id=employee.id,
            employee_code=employee_code,
            employee_name=employee.full_name,
            department_name=department_name,
            job_title_name=job_title_name,
            bhxh_code=None,
            health_care_insurance_code=None,
            health_care_family_participation=None,
            accident_insurance_code=None,
            bhyt_initial_clinic_name=None,
            company_bhxh_joined_date=None,
            participation_status="active",
            insurance_basis_amount=None,
            insurance_basis_source="contract",
            policy_version_id=None,
            policy_version_name=None,
            effective_regulation_code=None,
            company_region=None,
            has_component_overrides=False,
            employer_pays_on_behalf=False,
            contract_id=None,
            contract_number=None,
            contributions=[],
        )

    basis_amount, basis_source = _resolve_basis_amount(profile, current_contract)
    contributions = _compute_contributions(basis_amount, components, policy_rates, overrides)
    has_overrides = bool(overrides)
    employer_pays = any(s.employer_advances_employee_part for s in contributions)

    return EmployeeInsuranceListItem(
        employee_id=employee.id,
        employee_code=employee_code,
        employee_name=employee.full_name,
        department_name=department_name,
        job_title_name=job_title_name,
        bhxh_code=profile.bhxh_code,
        health_care_insurance_code=profile.health_care_insurance_code,
        health_care_family_participation=profile.health_care_family_participation,
        accident_insurance_code=profile.accident_insurance_code,
        bhyt_initial_clinic_name=profile.bhyt_initial_clinic_name,
        company_bhxh_joined_date=profile.company_bhxh_joined_date,
        participation_status=profile.participation_status,
        insurance_basis_amount=basis_amount,
        insurance_basis_source=basis_source,
        policy_version_id=policy.id if policy else None,
        policy_version_name=policy.name if policy else None,
        effective_regulation_code=policy.code if policy else None,
        company_region=policy.company_region if policy else None,
        has_component_overrides=has_overrides,
        employer_pays_on_behalf=employer_pays,
        contract_id=current_contract.id if current_contract else None,
        contract_number=current_contract.contract_number if current_contract else None,
        contributions=contributions,
    )


# ── Public service functions ───────────────────────────────────────────────────

async def get_employee_insurance_profile(
    session: AsyncSession,
    employee_id: int,
) -> Optional[EmployeeInsuranceProfile]:
    return (
        await session.execute(
            select(EmployeeInsuranceProfile).where(
                EmployeeInsuranceProfile.employee_id == employee_id
            )
        )
    ).scalar_one_or_none()


async def ensure_employee_insurance_profile(
    session: AsyncSession,
    employee: Employee,
) -> EmployeeInsuranceProfile:
    profile = await get_employee_insurance_profile(session, employee.id)
    if profile:
        return profile

    profile = EmployeeInsuranceProfile(
        employee_id=employee.id,
        bhxh_code=normalize_bhxh_code(employee.bhxh_code),
        participation_status=derive_participation_status(employee.status),
        insurance_basis_source="contract",
        created_at=_utcnow(),
    )
    session.add(profile)
    await session.flush()
    return profile


async def sync_employee_profile_from_employee(
    session: AsyncSession,
    employee: Employee,
) -> EmployeeInsuranceProfile:
    employee.bhxh_code = normalize_bhxh_code(employee.bhxh_code)
    profile = await ensure_employee_insurance_profile(session, employee)
    profile.bhxh_code = employee.bhxh_code
    profile.updated_at = _utcnow()
    return profile


async def list_insurance_profiles(
    session: AsyncSession,
    *,
    keyword: Optional[str] = None,
    department_id: Optional[int] = None,
    participation_status: Optional[str] = None,
    has_bhxh_code: Optional[bool] = None,
    joined_from: Optional[date] = None,
    joined_to: Optional[date] = None,
    policy_version_id: Optional[int] = None,
    has_component_overrides: Optional[bool] = None,
    employer_pays_on_behalf: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
) -> EmployeeInsuranceListPage:
    # Base query: employees LEFT JOIN profiles LEFT JOIN job records
    base_stmt = (
        select(
            Employee,
            EmployeeInsuranceProfile,
            Department.name.label("department_name"),
            JobTitle.name.label("job_title_name"),
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
        .outerjoin(JobTitle, JobTitle.id == EmployeeJobRecord.job_title_id)
    )

    # Apply filters
    if keyword:
        kw = f"%{keyword.strip().lower()}%"
        bhxh_like = f"%{keyword.strip()}%"
        base_stmt = base_stmt.where(
            Employee.normalized_name.ilike(kw)
            | Employee.bhxh_code.ilike(bhxh_like)
        )

    if department_id is not None:
        base_stmt = base_stmt.where(EmployeeJobRecord.department_id == department_id)

    if participation_status is not None:
        base_stmt = base_stmt.where(
            EmployeeInsuranceProfile.participation_status == participation_status
        )

    if has_bhxh_code is True:
        base_stmt = base_stmt.where(EmployeeInsuranceProfile.bhxh_code.is_not(None))
    elif has_bhxh_code is False:
        base_stmt = base_stmt.where(EmployeeInsuranceProfile.bhxh_code.is_(None))

    if joined_from is not None:
        base_stmt = base_stmt.where(
            EmployeeInsuranceProfile.company_bhxh_joined_date >= joined_from
        )
    if joined_to is not None:
        base_stmt = base_stmt.where(
            EmployeeInsuranceProfile.company_bhxh_joined_date <= joined_to
        )

    if policy_version_id is not None:
        base_stmt = base_stmt.where(
            EmployeeInsuranceProfile.insurance_policy_version_id == policy_version_id
        )

    if has_component_overrides is True:
        override_exists = (
            select(EmployeeInsuranceComponentOverride.id)
            .where(
                EmployeeInsuranceComponentOverride.employee_insurance_profile_id
                == EmployeeInsuranceProfile.id
            )
            .exists()
        )
        base_stmt = base_stmt.where(override_exists)
    elif has_component_overrides is False:
        override_exists = (
            select(EmployeeInsuranceComponentOverride.id)
            .where(
                EmployeeInsuranceComponentOverride.employee_insurance_profile_id
                == EmployeeInsuranceProfile.id
            )
            .exists()
        )
        base_stmt = base_stmt.where(~override_exists)

    # Employer pays on behalf: filter by existence of any override with advances=True
    if employer_pays_on_behalf is True:
        pays_subq = (
            select(EmployeeInsuranceComponentOverride.id)
            .where(
                EmployeeInsuranceComponentOverride.employee_insurance_profile_id
                == EmployeeInsuranceProfile.id,
                EmployeeInsuranceComponentOverride.employer_advances_employee_part.is_(True),
                EmployeeInsuranceComponentOverride.use_company_default.is_(False),
            )
            .exists()
        )
        base_stmt = base_stmt.where(pays_subq)
    elif employer_pays_on_behalf is False:
        pays_subq = (
            select(EmployeeInsuranceComponentOverride.id)
            .where(
                EmployeeInsuranceComponentOverride.employee_insurance_profile_id
                == EmployeeInsuranceProfile.id,
                EmployeeInsuranceComponentOverride.employer_advances_employee_part.is_(True),
                EmployeeInsuranceComponentOverride.use_company_default.is_(False),
            )
            .exists()
        )
        base_stmt = base_stmt.where(~pays_subq)

    # Count
    subq = base_stmt.subquery()
    count_result = await session.execute(select(func.count()).select_from(subq))
    total = count_result.scalar_one()

    # Paginate
    page_stmt = (
        base_stmt.order_by(Employee.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await session.execute(page_stmt)).all()

    if not rows:
        return EmployeeInsuranceListPage(items=[], total=total, page=page, page_size=page_size)

    employees_in_page = [row[0] for row in rows]
    profiles_in_page = [row[1] for row in rows]
    dept_names = [row[2] for row in rows]
    jt_names = [row[3] for row in rows]

    # Batch load employee codes
    code_map = await employee_code_service.batch_build_employee_display_codes(
        session, employees_in_page
    )

    # Batch load current contracts
    emp_ids = [e.id for e in employees_in_page]
    contract_rows = await session.execute(
        select(EmployeeContract)
        .where(
            EmployeeContract.employee_id.in_(emp_ids),
            EmployeeContract.status == "active",
        )
        .order_by(EmployeeContract.employee_id, EmployeeContract.effective_from.desc())
    )
    all_contracts = list(contract_rows.scalars().all())
    contract_map: dict[int, EmployeeContract] = {}
    for c in all_contracts:
        if c.employee_id not in contract_map:
            contract_map[c.employee_id] = c

    # Batch load overrides
    profile_ids = [p.id for p in profiles_in_page if p is not None]
    override_rows = await session.execute(
        select(EmployeeInsuranceComponentOverride).where(
            EmployeeInsuranceComponentOverride.employee_insurance_profile_id.in_(profile_ids)
        )
    )
    all_overrides = list(override_rows.scalars().all())
    overrides_map: dict[int, dict[str, EmployeeInsuranceComponentOverride]] = {}
    for o in all_overrides:
        overrides_map.setdefault(o.employee_insurance_profile_id, {})[o.component_code] = o

    # Load active policy and components once
    active_policy = await _get_active_policy(session)
    components = await _get_components(session)
    policy_rates: dict[str, InsurancePolicyComponentRate] = {}
    if active_policy:
        policy_rates = await _get_policy_rates(session, active_policy.id)

    # Build pinned policy map for profiles that have a custom policy_version_id
    pinned_policy_ids = {
        p.insurance_policy_version_id
        for p in profiles_in_page
        if p and p.insurance_policy_version_id and p.insurance_policy_version_id != (active_policy.id if active_policy else None)
    }
    pinned_policies: dict[int, InsurancePolicyVersion] = {}
    pinned_rates: dict[int, dict[str, InsurancePolicyComponentRate]] = {}
    for pid in pinned_policy_ids:
        pv = await session.get(InsurancePolicyVersion, pid)
        if pv:
            pinned_policies[pid] = pv
            pinned_rates[pid] = await _get_policy_rates(session, pid)

    # Build items
    items: list[EmployeeInsuranceListItem] = []
    for emp, profile, dept_name, jt_name in zip(
        employees_in_page, profiles_in_page, dept_names, jt_names
    ):
        employee_code = code_map.get(emp.id, str(emp.employee_seq))
        current_contract = contract_map.get(emp.id)
        emp_overrides = overrides_map.get(profile.id, {}) if profile else {}

        # Resolve policy for this employee
        if profile and profile.insurance_policy_version_id and profile.insurance_policy_version_id in pinned_policies:
            emp_policy = pinned_policies[profile.insurance_policy_version_id]
            emp_policy_rates = pinned_rates[profile.insurance_policy_version_id]
        else:
            emp_policy = active_policy
            emp_policy_rates = policy_rates

        item = await _build_list_item(
            employee=emp,
            employee_code=employee_code,
            profile=profile,
            department_name=dept_name,
            job_title_name=jt_name,
            current_contract=current_contract,
            components=components,
            policy=emp_policy,
            policy_rates=emp_policy_rates,
            overrides=emp_overrides,
        )
        items.append(item)

    return EmployeeInsuranceListPage(items=items, total=total, page=page, page_size=page_size)


async def get_insurance_profile_detail(
    session: AsyncSession,
    employee_id: int,
) -> EmployeeInsuranceProfileRead:
    employee = await session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    profile = await get_employee_insurance_profile(session, employee_id)
    if not profile:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Nhân viên chưa có hồ sơ bảo hiểm",
        )

    # Job record
    job_row = (
        await session.execute(
            select(EmployeeJobRecord).where(
                EmployeeJobRecord.employee_id == employee_id,
                EmployeeJobRecord.is_current.is_(True),
            )
        )
    ).scalar_one_or_none()

    dept_name: Optional[str] = None
    jt_name: Optional[str] = None
    if job_row:
        if job_row.department_id:
            dept = await session.get(Department, job_row.department_id)
            dept_name = dept.name if dept else None
        if job_row.job_title_id:
            jt = await session.get(JobTitle, job_row.job_title_id)
            jt_name = jt.name if jt else None

    # Current contract
    contract_row = (
        await session.execute(
            select(EmployeeContract)
            .where(
                EmployeeContract.employee_id == employee_id,
                EmployeeContract.status == "active",
            )
            .order_by(EmployeeContract.effective_from.desc(), EmployeeContract.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    # Overrides
    override_rows = await session.execute(
        select(EmployeeInsuranceComponentOverride).where(
            EmployeeInsuranceComponentOverride.employee_insurance_profile_id == profile.id
        )
    )
    overrides = {o.component_code: o for o in override_rows.scalars().all()}

    # Policy
    active_policy = await _get_active_policy(session)
    policy = await _resolve_profile_policy(session, profile, active_policy)
    components = await _get_components(session)
    policy_rates = await _get_policy_rates(session, policy.id) if policy else {}

    # Compute
    employee_code = await employee_code_service.build_employee_display_code(session, employee)
    basis_amount, basis_source = _resolve_basis_amount(profile, contract_row)
    contributions = _compute_contributions(basis_amount, components, policy_rates, overrides)
    has_overrides = bool(overrides)
    employer_pays = any(s.employer_advances_employee_part for s in contributions)

    return EmployeeInsuranceProfileRead(
        id=profile.id,
        employee_id=employee.id,
        employee_code=employee_code,
        employee_name=employee.full_name,
        department_name=dept_name,
        job_title_name=jt_name,
        bhxh_code=profile.bhxh_code,
        health_care_insurance_code=profile.health_care_insurance_code,
        health_care_family_participation=profile.health_care_family_participation,
        accident_insurance_code=profile.accident_insurance_code,
        bhyt_initial_clinic_name=profile.bhyt_initial_clinic_name,
        bhyt_initial_clinic_code=profile.bhyt_initial_clinic_code,
        company_bhxh_joined_date=profile.company_bhxh_joined_date,
        participation_status=profile.participation_status,
        status_effective_from=profile.status_effective_from,
        status_note=profile.status_note,
        insurance_basis_source=basis_source,
        insurance_basis_amount=basis_amount,
        policy_version_id=policy.id if policy else None,
        policy_version_name=policy.name if policy else None,
        effective_regulation_code=policy.code if policy else None,
        company_region=policy.company_region if policy else None,
        has_component_overrides=has_overrides,
        employer_pays_on_behalf=employer_pays,
        contract_id=contract_row.id if contract_row else None,
        contract_number=contract_row.contract_number if contract_row else None,
        contributions=contributions,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


async def upsert_insurance_profile(
    session: AsyncSession,
    employee_id: int,
    payload: EmployeeInsuranceProfileUpdate,
) -> EmployeeInsuranceProfileRead:
    employee = await session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")

    profile = await get_employee_insurance_profile(session, employee_id)
    is_new_profile = profile is None
    if is_new_profile:
        profile = EmployeeInsuranceProfile(
            employee_id=employee_id,
            insurance_basis_source="contract",
            participation_status="active",
            created_at=_utcnow(),
        )
        session.add(profile)
        await session.flush()

    # Validate overrides: component codes must exist
    if payload.component_overrides:
        components = await _get_components(session)
        valid_codes = {c.code for c in components}
        for ov in payload.component_overrides:
            if ov.component_code not in valid_codes:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Component code không hợp lệ: {ov.component_code}",
                )

    # Capture old status: None for brand-new profile (triggers new_hire event)
    old_status: Optional[str] = None if is_new_profile else profile.participation_status

    # Update profile fields
    profile.bhxh_code = normalize_bhxh_code(payload.bhxh_code)
    profile.health_care_insurance_code = normalize_optional_insurance_code(
        payload.health_care_insurance_code
    )
    profile.health_care_family_participation = payload.health_care_family_participation
    profile.accident_insurance_code = normalize_optional_insurance_code(
        payload.accident_insurance_code
    )
    profile.bhyt_initial_clinic_name = payload.bhyt_initial_clinic_name
    profile.bhyt_initial_clinic_code = payload.bhyt_initial_clinic_code
    profile.company_bhxh_joined_date = payload.company_bhxh_joined_date
    profile.participation_status = payload.participation_status
    profile.status_effective_from = payload.status_effective_from
    profile.status_note = payload.status_note
    profile.insurance_basis_source = payload.insurance_basis_source
    profile.insurance_basis_amount = (
        payload.insurance_basis_amount
        if payload.insurance_basis_source == "manual_fixed"
        else None
    )
    profile.updated_at = _utcnow()

    if not payload.health_care_family_participation:
        relative_rows = await session.execute(
            select(EmployeeRelative).where(EmployeeRelative.employee_id == employee_id)
        )
        for relative in relative_rows.scalars().all():
            relative.participates_in_health_care_insurance = False

    # Also sync bhxh_code to employees table for compatibility
    employee.bhxh_code = profile.bhxh_code

    await session.flush()

    # Replace component overrides
    existing_overrides = (
        await session.execute(
            select(EmployeeInsuranceComponentOverride).where(
                EmployeeInsuranceComponentOverride.employee_insurance_profile_id == profile.id
            )
        )
    ).scalars().all()
    for ov in existing_overrides:
        await session.delete(ov)
    await session.flush()

    for ov_input in payload.component_overrides:
        new_ov = EmployeeInsuranceComponentOverride(
            employee_insurance_profile_id=profile.id,
            component_code=ov_input.component_code,
            use_company_default=ov_input.use_company_default,
            fixed_employee_amount=ov_input.fixed_employee_amount,
            fixed_employer_amount=ov_input.fixed_employer_amount,
            employer_advances_employee_part=ov_input.employer_advances_employee_part,
            created_at=_utcnow(),
        )
        session.add(new_ov)

    await session.commit()

    # Auto-record biến động nếu trạng thái thay đổi
    if old_status != profile.participation_status:
        effective_date = payload.status_effective_from or date.today()
        await insurance_change_service.record_status_change(
            session=session,
            employee_id=employee_id,
            old_status=old_status,
            new_status=profile.participation_status,
            profile=profile,
            effective_date=effective_date,
        )
        await session.commit()

    return await get_insurance_profile_detail(session, employee_id)
