"""Service quản lý hợp đồng lao động nhân viên (4.1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import ContractCategory
from app.models.employee import Employee
from app.models.employee_contract import EmployeeContract
from app.models.employee_insurance import EmployeeInsuranceProfile
from app.models.employee_job import EmployeeJobRecord
from app.models.salary import (
    BhxhPositionGroup,
    BhxhSenioritySetting,
    CompanyBhxhRegion,
    RegionalMinimumWage,
    SalaryScale,
    SalaryScaleEntry,
)
from app.schemas.employee_contract import (
    ALLOWED_INSURANCE_SALARY_MODES,
    ContractCreate,
    ContractInsuranceSalaryPreviewInput,
    ContractInsuranceSalaryPreviewRead,
    ContractListPage,
    ContractRead,
    ContractUpdate,
    _days_until,
    _effective_status,
    _status_display,
)
from app.services import employee_code_service
from app.utils.contract_status import contract_effective_status_expr, effective_contract_status


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class ResolvedContractInsuranceSalary:
    insurance_salary_mode: str
    insurance_salary: Optional[Decimal]
    bhxh_position_group_id: Optional[int]
    bhxh_position_group_code: Optional[str]
    bhxh_position_group_name: Optional[str]
    insurance_salary_grade_no: Optional[int]
    resolved_insurance_salary_grade_no: Optional[int]
    bhxh_seniority_start_date: Optional[date]
    bhxh_seniority_start_source: Optional[str]
    insurance_salary_fixed_amount: Optional[Decimal]
    company_region: Optional[int]
    regional_minimum_wage: Optional[Decimal]
    salary_scale_id: Optional[int]
    salary_scale_name: Optional[str]
    coefficient: Optional[Decimal]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_read(
    c: EmployeeContract,
    category_name: str,
    appendices: list[ContractRead] | None = None,
    employee_name: str | None = None,
    employee_code: str | None = None,
    position_group: BhxhPositionGroup | None = None,
    resolved_grade_no: int | None = None,
) -> ContractRead:
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
        insurance_salary_mode=c.insurance_salary_mode,
        bhxh_position_group_id=c.bhxh_position_group_id,
        bhxh_position_group_code=position_group.code if position_group else None,
        bhxh_position_group_name=position_group.name if position_group else None,
        insurance_salary_grade_no=c.insurance_salary_grade_no,
        resolved_insurance_salary_grade_no=resolved_grade_no,
        bhxh_seniority_start_date=c.bhxh_seniority_start_date,
        insurance_salary_fixed_amount=c.insurance_salary_fixed_amount,
        status=_effective_status(c.status, c.effective_to),
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
        employee_name=employee_name,
        employee_code=employee_code,
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


async def _build_position_group_map(
    session: AsyncSession,
    contracts: list[EmployeeContract],
) -> dict[int, BhxhPositionGroup]:
    group_ids = {
        c.bhxh_position_group_id
        for c in contracts
        if c.bhxh_position_group_id is not None
    }
    if not group_ids:
        return {}
    rows = await session.execute(
        select(BhxhPositionGroup).where(BhxhPositionGroup.id.in_(group_ids))
    )
    return {group.id: group for group in rows.scalars().all()}


async def _get_position_group_or_404(
    session: AsyncSession,
    group_id: int,
) -> BhxhPositionGroup:
    group = await session.get(BhxhPositionGroup, group_id)
    if not group:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy nhóm vị trí BHXH",
        )
    return group


async def _get_company_region_as_of(
    session: AsyncSession,
    as_of_date: date,
) -> CompanyBhxhRegion:
    rows = await session.execute(
        select(CompanyBhxhRegion)
        .where(
            CompanyBhxhRegion.effective_from <= as_of_date,
            (CompanyBhxhRegion.effective_to.is_(None)) | (CompanyBhxhRegion.effective_to >= as_of_date),
        )
        .order_by(CompanyBhxhRegion.effective_from.desc(), CompanyBhxhRegion.id.desc())
    )
    item = rows.scalars().first()
    if not item:
        fallback_rows = await session.execute(
            select(CompanyBhxhRegion)
            .order_by(CompanyBhxhRegion.effective_from.asc(), CompanyBhxhRegion.id.asc())
        )
        item = fallback_rows.scalars().first()
    if not item:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chưa có cấu hình vùng BHXH công ty hiệu lực cho ngày này",
        )
    return item


async def _get_minimum_wage_as_of(
    session: AsyncSession,
    region: int,
    as_of_date: date,
) -> RegionalMinimumWage:
    rows = await session.execute(
        select(RegionalMinimumWage)
        .where(
            RegionalMinimumWage.region == region,
            RegionalMinimumWage.effective_from <= as_of_date,
            (RegionalMinimumWage.effective_to.is_(None)) | (RegionalMinimumWage.effective_to >= as_of_date),
        )
        .order_by(RegionalMinimumWage.effective_from.desc(), RegionalMinimumWage.id.desc())
    )
    item = rows.scalars().first()
    if not item:
        fallback_rows = await session.execute(
            select(RegionalMinimumWage)
            .where(RegionalMinimumWage.region == region)
            .order_by(RegionalMinimumWage.effective_from.asc(), RegionalMinimumWage.id.asc())
        )
        item = fallback_rows.scalars().first()
    if not item:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chưa có cấu hình lương tối thiểu vùng hiệu lực cho ngày này",
        )
    return item


async def _get_salary_scale_as_of(
    session: AsyncSession,
    as_of_date: date,
) -> SalaryScale:
    rows = await session.execute(
        select(SalaryScale)
        .where(
            SalaryScale.effective_from <= as_of_date,
            (SalaryScale.effective_to.is_(None)) | (SalaryScale.effective_to >= as_of_date),
        )
        .order_by(SalaryScale.effective_from.desc(), SalaryScale.id.desc())
    )
    item = rows.scalars().first()
    if not item:
        fallback_rows = await session.execute(
            select(SalaryScale)
            .order_by(SalaryScale.effective_from.asc(), SalaryScale.id.asc())
        )
        item = fallback_rows.scalars().first()
    if not item:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chưa có thang bảng lương hiệu lực cho ngày này",
        )
    return item


async def _get_seniority_setting_as_of(
    session: AsyncSession,
    as_of_date: date,
) -> BhxhSenioritySetting:
    rows = await session.execute(
        select(BhxhSenioritySetting)
        .where(
            BhxhSenioritySetting.effective_from <= as_of_date,
            (BhxhSenioritySetting.effective_to.is_(None)) | (BhxhSenioritySetting.effective_to >= as_of_date),
        )
        .order_by(BhxhSenioritySetting.effective_from.desc(), BhxhSenioritySetting.id.desc())
    )
    item = rows.scalars().first()
    if not item:
        fallback_rows = await session.execute(
            select(BhxhSenioritySetting)
            .order_by(BhxhSenioritySetting.effective_from.asc(), BhxhSenioritySetting.id.asc())
        )
        item = fallback_rows.scalars().first()
    if not item:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chưa có rule thâm niên BHXH hiệu lực cho ngày này",
        )
    return item


async def _resolve_contract_seniority_start_date(
    session: AsyncSession,
    employee_id: int,
) -> tuple[date, str]:
    profile_row = await session.execute(
        select(EmployeeInsuranceProfile.company_bhxh_joined_date).where(
            EmployeeInsuranceProfile.employee_id == employee_id
        )
    )
    company_joined_date = profile_row.scalar_one_or_none()
    if company_joined_date is not None:
        return company_joined_date, "employee_insurance_profiles.company_bhxh_joined_date"

    current_job_row = await session.execute(
        select(EmployeeJobRecord)
        .where(
            EmployeeJobRecord.employee_id == employee_id,
            EmployeeJobRecord.is_current.is_(True),
        )
        .order_by(EmployeeJobRecord.effective_from.desc(), EmployeeJobRecord.id.desc())
    )
    current_job = current_job_row.scalars().first()
    if current_job and current_job.official_date is not None:
        return current_job.official_date, "employee_job_records.official_date"

    employee = await session.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy nhân viên")
    return employee.start_date, "employees.start_date"


def _build_raise_date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Rule thâm niên BHXH có ngày nâng bậc không hợp lệ",
        ) from exc


def _resolve_seniority_grade(
    *,
    seniority_start_date: date,
    as_of_date: date,
    initial_grade_no: int,
    setting: BhxhSenioritySetting,
) -> int:
    if initial_grade_no < 1:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="insurance_salary_grade_no phải >= 1",
        )

    cutoff_tuple = (setting.first_year_cutoff_month, setting.first_year_cutoff_day)
    start_tuple = (seniority_start_date.month, seniority_start_date.day)
    counted_start_year = (
        seniority_start_date.year
        if start_tuple <= cutoff_tuple
        else seniority_start_date.year + 1
    )

    resolved_grade = initial_grade_no
    cycle_year = counted_start_year + setting.years_per_grade
    while resolved_grade < 7 and cycle_year <= as_of_date.year:
        if _build_raise_date(cycle_year, setting.raise_month, setting.raise_day) <= as_of_date:
            resolved_grade += 1
        cycle_year += setting.years_per_grade
    return min(resolved_grade, 7)


def _normalize_contract_mode(
    mode: Optional[str],
    *,
    bhxh_position_group_id: Optional[int],
    insurance_salary_grade_no: Optional[int],
    insurance_salary_fixed_amount: Optional[Decimal],
    insurance_salary: Optional[Decimal],
) -> str:
    if mode:
        if mode not in ALLOWED_INSURANCE_SALARY_MODES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"insurance_salary_mode phải là một trong: {sorted(ALLOWED_INSURANCE_SALARY_MODES)}",
            )
        return mode
    if bhxh_position_group_id is not None or insurance_salary_grade_no is not None:
        return "computed_by_position_group"
    if insurance_salary_fixed_amount is not None or insurance_salary is not None:
        return "fixed_manual"
    return "fixed_manual"


async def _resolve_contract_insurance_salary(
    session: AsyncSession,
    *,
    employee_id: int,
    effective_from: date,
    insurance_salary_mode: str,
    bhxh_position_group_id: Optional[int],
    insurance_salary_grade_no: Optional[int],
    bhxh_seniority_start_date: Optional[date],
    insurance_salary_fixed_amount: Optional[Decimal],
    insurance_salary: Optional[Decimal],
    allow_empty_fixed_amount: bool = False,
) -> ResolvedContractInsuranceSalary:
    mode = _normalize_contract_mode(
        insurance_salary_mode,
        bhxh_position_group_id=bhxh_position_group_id,
        insurance_salary_grade_no=insurance_salary_grade_no,
        insurance_salary_fixed_amount=insurance_salary_fixed_amount,
        insurance_salary=insurance_salary,
    )

    if mode == "fixed_manual":
        fixed_amount = insurance_salary_fixed_amount
        if fixed_amount is None:
            fixed_amount = insurance_salary
        if fixed_amount is None:
            if allow_empty_fixed_amount:
                return ResolvedContractInsuranceSalary(
                    insurance_salary_mode=mode,
                    insurance_salary=None,
                    bhxh_position_group_id=None,
                    bhxh_position_group_code=None,
                    bhxh_position_group_name=None,
                    insurance_salary_grade_no=None,
                    resolved_insurance_salary_grade_no=None,
                    bhxh_seniority_start_date=None,
                    bhxh_seniority_start_source=None,
                    insurance_salary_fixed_amount=None,
                    company_region=None,
                    regional_minimum_wage=None,
                    salary_scale_id=None,
                    salary_scale_name=None,
                    coefficient=None,
                )
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Mode fixed_manual yêu cầu nhập mức lương đóng BH cố định > 0",
            )
        if fixed_amount <= 0:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Mode fixed_manual yêu cầu nhập mức lương đóng BH cố định > 0",
            )
        fixed_amount = Decimal(str(fixed_amount)).quantize(Decimal("0.01"))
        return ResolvedContractInsuranceSalary(
            insurance_salary_mode=mode,
            insurance_salary=fixed_amount,
            bhxh_position_group_id=None,
            bhxh_position_group_code=None,
            bhxh_position_group_name=None,
            insurance_salary_grade_no=None,
            resolved_insurance_salary_grade_no=None,
            bhxh_seniority_start_date=None,
            bhxh_seniority_start_source=None,
            insurance_salary_fixed_amount=fixed_amount,
            company_region=None,
            regional_minimum_wage=None,
            salary_scale_id=None,
            salary_scale_name=None,
            coefficient=None,
        )

    if bhxh_position_group_id is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mode computed_by_position_group yêu cầu chọn nhóm vị trí BHXH",
        )
    if insurance_salary_grade_no is None or insurance_salary_grade_no < 1 or insurance_salary_grade_no > 7:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mode computed_by_position_group yêu cầu chọn bậc hệ số từ 1 đến 7",
        )

    group = await _get_position_group_or_404(session, bhxh_position_group_id)
    company_region = await _get_company_region_as_of(session, effective_from)
    minimum_wage = await _get_minimum_wage_as_of(session, company_region.region, effective_from)
    salary_scale = await _get_salary_scale_as_of(session, effective_from)
    seniority_setting = await _get_seniority_setting_as_of(session, effective_from)

    seniority_start_source: Optional[str] = None
    resolved_seniority_start_date = bhxh_seniority_start_date
    if resolved_seniority_start_date is None:
        resolved_seniority_start_date, seniority_start_source = await _resolve_contract_seniority_start_date(
            session,
            employee_id,
        )

    resolved_grade_no = _resolve_seniority_grade(
        seniority_start_date=resolved_seniority_start_date,
        as_of_date=effective_from,
        initial_grade_no=insurance_salary_grade_no,
        setting=seniority_setting,
    )

    entry_rows = await session.execute(
        select(SalaryScaleEntry).where(
            SalaryScaleEntry.salary_scale_id == salary_scale.id,
            SalaryScaleEntry.bhxh_position_group_id == bhxh_position_group_id,
            SalaryScaleEntry.grade_no == resolved_grade_no,
        )
    )
    entry = entry_rows.scalars().first()
    if not entry:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Nhóm vị trí BHXH chưa có cấu hình hệ số cho bậc áp dụng trong thang bảng lương hiệu lực",
        )

    coefficient = Decimal(str(entry.coefficient)).quantize(Decimal("0.0001"))
    regional_minimum_wage = Decimal(str(minimum_wage.amount)).quantize(Decimal("1"))
    computed_amount = (regional_minimum_wage * coefficient).quantize(Decimal("0.01"))

    return ResolvedContractInsuranceSalary(
        insurance_salary_mode=mode,
        insurance_salary=computed_amount,
        bhxh_position_group_id=group.id,
        bhxh_position_group_code=group.code,
        bhxh_position_group_name=group.name,
        insurance_salary_grade_no=insurance_salary_grade_no,
        resolved_insurance_salary_grade_no=resolved_grade_no,
        bhxh_seniority_start_date=resolved_seniority_start_date,
        bhxh_seniority_start_source=seniority_start_source,
        insurance_salary_fixed_amount=None,
        company_region=company_region.region,
        regional_minimum_wage=regional_minimum_wage,
        salary_scale_id=salary_scale.id,
        salary_scale_name=salary_scale.name,
        coefficient=coefficient,
    )


async def _resolve_contract_read_grade_no(
    session: AsyncSession,
    contract: EmployeeContract,
) -> int | None:
    if (
        contract.insurance_salary_mode != "computed_by_position_group"
        or contract.insurance_salary_grade_no is None
    ):
        return None

    seniority_start_date = contract.bhxh_seniority_start_date
    if seniority_start_date is None:
        seniority_start_date, _ = await _resolve_contract_seniority_start_date(
            session,
            contract.employee_id,
        )

    setting = await _get_seniority_setting_as_of(session, contract.effective_from)
    return _resolve_seniority_grade(
        seniority_start_date=seniority_start_date,
        as_of_date=contract.effective_from,
        initial_grade_no=contract.insurance_salary_grade_no,
        setting=setting,
    )


async def _ensure_insurance_profile(
    session: AsyncSession,
    employee_id: int,
) -> EmployeeInsuranceProfile:
    row = await session.execute(
        select(EmployeeInsuranceProfile).where(
            EmployeeInsuranceProfile.employee_id == employee_id
        )
    )
    profile = row.scalars().first()
    if profile:
        return profile

    profile = EmployeeInsuranceProfile(
        employee_id=employee_id,
        participation_status="active",
        insurance_basis_source="contract",
        created_at=_utcnow(),
    )
    session.add(profile)
    await session.flush()
    return profile


async def _get_latest_active_contract_for_basis(
    session: AsyncSession,
    employee_id: int,
) -> EmployeeContract | None:
    today = date.today()
    row = await session.execute(
        select(EmployeeContract)
        .where(
            EmployeeContract.employee_id == employee_id,
            contract_effective_status_expr(
                status_col=EmployeeContract.status,
                effective_to_col=EmployeeContract.effective_to,
                today=today,
            ) == "active",
            EmployeeContract.insurance_salary.is_not(None),
        )
        .order_by(
            EmployeeContract.effective_from.desc(),
            EmployeeContract.id.desc(),
        )
        .limit(1)
    )
    return row.scalars().first()


async def _sync_employee_insurance_profile_from_contracts(
    session: AsyncSession,
    employee_id: int,
) -> None:
    profile = await _ensure_insurance_profile(session, employee_id)
    if profile.insurance_basis_source == "manual_fixed":
        return

    active_contract = await _get_latest_active_contract_for_basis(session, employee_id)
    if active_contract is None:
        profile.insurance_basis_source = "contract"
        profile.insurance_basis_amount = None
    else:
        profile.insurance_basis_source = (
            "computed"
            if active_contract.insurance_salary_mode == "computed_by_position_group"
            else "contract"
        )
        profile.insurance_basis_amount = active_contract.insurance_salary
        if (
            profile.company_bhxh_joined_date is None
            and active_contract.bhxh_seniority_start_date is not None
        ):
            profile.company_bhxh_joined_date = active_contract.bhxh_seniority_start_date

    profile.updated_at = _utcnow()
    session.add(profile)
    await session.flush()


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
    group_map = await _build_position_group_map(session, all_contracts)

    # Phân nhóm: HĐ gốc và phụ lục
    appendix_map: dict[int, list[ContractRead]] = {}
    for c in all_contracts:
        if c.parent_contract_id is not None:
            resolved_grade_no = await _resolve_contract_read_grade_no(session, c)
            appendix_map.setdefault(c.parent_contract_id, []).append(
                _to_read(
                    c,
                    cat_map.get(c.contract_category_id, ""),
                    position_group=group_map.get(c.bhxh_position_group_id),
                    resolved_grade_no=resolved_grade_no,
                )
            )

    result: list[ContractRead] = []
    for c in all_contracts:
        if c.parent_contract_id is None:
            resolved_grade_no = await _resolve_contract_read_grade_no(session, c)
            result.append(
                _to_read(
                    c,
                    cat_map.get(c.contract_category_id, ""),
                    appendix_map.get(c.id, []),
                    position_group=group_map.get(c.bhxh_position_group_id),
                    resolved_grade_no=resolved_grade_no,
                )
            )

    return result


async def get_contract_detail(session: AsyncSession, employee_id: int, contract_id: int) -> ContractRead:
    c = await _get_contract_or_404(session, employee_id, contract_id)
    cat = await session.get(ContractCategory, c.contract_category_id)
    cat_name = cat.name if cat else ""
    group = await session.get(BhxhPositionGroup, c.bhxh_position_group_id) if c.bhxh_position_group_id else None

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
        sub_group_map = await _build_position_group_map(session, sub)
        appendices = [
            _to_read(
                s,
                sub_cat_map.get(s.contract_category_id, ""),
                position_group=sub_group_map.get(s.bhxh_position_group_id),
                resolved_grade_no=await _resolve_contract_read_grade_no(session, s),
            )
            for s in sub
        ]

    resolved_grade_no = await _resolve_contract_read_grade_no(session, c)
    return _to_read(
        c,
        cat_name,
        appendices,
        position_group=group,
        resolved_grade_no=resolved_grade_no,
    )


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

    resolved_salary = await _resolve_contract_insurance_salary(
        session,
        employee_id=employee_id,
        effective_from=payload.effective_from,
        insurance_salary_mode=payload.insurance_salary_mode,
        bhxh_position_group_id=payload.bhxh_position_group_id,
        insurance_salary_grade_no=payload.insurance_salary_grade_no,
        bhxh_seniority_start_date=payload.bhxh_seniority_start_date,
        insurance_salary_fixed_amount=payload.insurance_salary_fixed_amount,
        insurance_salary=payload.insurance_salary,
    )

    c = EmployeeContract(
        employee_id=employee_id,
        parent_contract_id=payload.parent_contract_id,
        contract_category_id=payload.contract_category_id,
        document_kind=cat.document_kind,
        contract_number=payload.contract_number,
        signed_date=payload.signed_date,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        insurance_salary=resolved_salary.insurance_salary,
        insurance_salary_mode=resolved_salary.insurance_salary_mode,
        bhxh_position_group_id=resolved_salary.bhxh_position_group_id,
        insurance_salary_grade_no=resolved_salary.insurance_salary_grade_no,
        bhxh_seniority_start_date=resolved_salary.bhxh_seniority_start_date,
        insurance_salary_fixed_amount=resolved_salary.insurance_salary_fixed_amount,
        notes=payload.notes,
        status=effective_contract_status("active", payload.effective_to),
        created_by=created_by,
        created_at=_utcnow(),
    )
    session.add(c)
    await session.flush()
    await _sync_employee_insurance_profile_from_contracts(session, employee_id)
    await session.commit()
    await session.refresh(c)
    group = await session.get(BhxhPositionGroup, c.bhxh_position_group_id) if c.bhxh_position_group_id else None
    return _to_read(
        c,
        cat.name,
        position_group=group,
        resolved_grade_no=resolved_salary.resolved_insurance_salary_grade_no,
    )


async def preview_contract_insurance_salary(
    session: AsyncSession,
    employee_id: int,
    payload: ContractInsuranceSalaryPreviewInput,
) -> ContractInsuranceSalaryPreviewRead:
    resolved = await _resolve_contract_insurance_salary(
        session,
        employee_id=employee_id,
        effective_from=payload.effective_from,
        insurance_salary_mode=payload.insurance_salary_mode,
        bhxh_position_group_id=payload.bhxh_position_group_id,
        insurance_salary_grade_no=payload.insurance_salary_grade_no,
        bhxh_seniority_start_date=None,
        insurance_salary_fixed_amount=payload.insurance_salary_fixed_amount,
        insurance_salary=None,
    )
    return ContractInsuranceSalaryPreviewRead(
        insurance_salary_mode=resolved.insurance_salary_mode,
        insurance_salary=resolved.insurance_salary,
        bhxh_position_group_id=resolved.bhxh_position_group_id,
        bhxh_position_group_code=resolved.bhxh_position_group_code,
        bhxh_position_group_name=resolved.bhxh_position_group_name,
        insurance_salary_grade_no=resolved.insurance_salary_grade_no,
        resolved_insurance_salary_grade_no=resolved.resolved_insurance_salary_grade_no,
        bhxh_seniority_start_date=resolved.bhxh_seniority_start_date,
        bhxh_seniority_start_source=resolved.bhxh_seniority_start_source,
        insurance_salary_fixed_amount=resolved.insurance_salary_fixed_amount,
        company_region=resolved.company_region,
        regional_minimum_wage=resolved.regional_minimum_wage,
        salary_scale_id=resolved.salary_scale_id,
        salary_scale_name=resolved.salary_scale_name,
        coefficient=resolved.coefficient,
    )


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

    if payload.signed_date is not None:
        c.signed_date = payload.signed_date
    if payload.effective_from is not None:
        c.effective_from = payload.effective_from
    if payload.effective_to is not None:
        c.effective_to = payload.effective_to
    if payload.notes is not None:
        c.notes = payload.notes
    if payload.status == "terminated":
        c.status = "terminated"

    # Validate dates sau khi patch
    if c.effective_to and c.effective_to < c.effective_from:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="effective_to phải >= effective_from")

    next_mode = payload.insurance_salary_mode or c.insurance_salary_mode
    next_fixed_amount = (
        payload.insurance_salary_fixed_amount
        if payload.insurance_salary_fixed_amount is not None
        else (
            payload.insurance_salary
            if payload.insurance_salary is not None and next_mode == "fixed_manual"
            else c.insurance_salary_fixed_amount
        )
    )

    resolved_salary = await _resolve_contract_insurance_salary(
        session,
        employee_id=employee_id,
        effective_from=c.effective_from,
        insurance_salary_mode=next_mode,
        bhxh_position_group_id=(
            payload.bhxh_position_group_id
            if payload.bhxh_position_group_id is not None
            else c.bhxh_position_group_id
        ),
        insurance_salary_grade_no=(
            payload.insurance_salary_grade_no
            if payload.insurance_salary_grade_no is not None
            else c.insurance_salary_grade_no
        ),
        bhxh_seniority_start_date=(
            payload.bhxh_seniority_start_date
            if payload.bhxh_seniority_start_date is not None
            else c.bhxh_seniority_start_date
        ),
        insurance_salary_fixed_amount=next_fixed_amount,
        insurance_salary=(
            payload.insurance_salary
            if payload.insurance_salary is not None
            else c.insurance_salary
        ),
        allow_empty_fixed_amount=(
            payload.insurance_salary_mode is None
            and payload.insurance_salary is None
            and payload.insurance_salary_fixed_amount is None
            and c.insurance_salary_mode == "fixed_manual"
        ),
    )
    c.insurance_salary = resolved_salary.insurance_salary
    c.insurance_salary_mode = resolved_salary.insurance_salary_mode
    c.bhxh_position_group_id = resolved_salary.bhxh_position_group_id
    c.insurance_salary_grade_no = resolved_salary.insurance_salary_grade_no
    c.bhxh_seniority_start_date = resolved_salary.bhxh_seniority_start_date
    c.insurance_salary_fixed_amount = resolved_salary.insurance_salary_fixed_amount
    if c.status != "terminated":
        base_status = "draft" if c.status == "draft" else "active"
        c.status = effective_contract_status(base_status, c.effective_to)

    c.updated_at = _utcnow()
    session.add(c)
    await session.flush()
    await _sync_employee_insurance_profile_from_contracts(session, employee_id)
    await session.commit()
    await session.refresh(c)

    cat = await session.get(ContractCategory, c.contract_category_id)
    group = await session.get(BhxhPositionGroup, c.bhxh_position_group_id) if c.bhxh_position_group_id else None
    return _to_read(
        c,
        cat.name if cat else "",
        position_group=group,
        resolved_grade_no=resolved_salary.resolved_insurance_salary_grade_no,
    )


async def terminate_contract(session: AsyncSession, employee_id: int, contract_id: int) -> ContractRead:
    c = await _get_contract_or_404(session, employee_id, contract_id)
    if c.status == "terminated":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Hợp đồng đã ở trạng thái hủy")
    c.status = "terminated"
    c.updated_at = _utcnow()
    session.add(c)
    await session.flush()
    await _sync_employee_insurance_profile_from_contracts(session, employee_id)
    await session.commit()
    await session.refresh(c)
    cat = await session.get(ContractCategory, c.contract_category_id)
    group = await session.get(BhxhPositionGroup, c.bhxh_position_group_id) if c.bhxh_position_group_id else None
    resolved_grade_no = await _resolve_contract_read_grade_no(session, c)
    return _to_read(c, cat.name if cat else "", position_group=group, resolved_grade_no=resolved_grade_no)


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
    group = await session.get(BhxhPositionGroup, c.bhxh_position_group_id) if c.bhxh_position_group_id else None
    resolved_grade_no = await _resolve_contract_read_grade_no(session, c)
    return _to_read(c, cat.name if cat else "", position_group=group, resolved_grade_no=resolved_grade_no)


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

    today = date.today()
    effective_status_expr = contract_effective_status_expr(
        status_col=EmployeeContract.status,
        effective_to_col=EmployeeContract.effective_to,
        today=today,
    )

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
        q = q.where(effective_status_expr == status)
    if category_id:
        q = q.where(EmployeeContract.contract_category_id == category_id)
    if expiring_within is not None:
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
    contracts = [contract for contract, _, _ in rows]
    group_map = await _build_position_group_map(session, contracts)
    employees = [emp for _, _, emp in rows]
    code_map = await employee_code_service.batch_build_employee_display_codes(session, employees)
    items = [
        _to_read(
            c,
            cat.name,
            employee_name=emp.full_name,
            employee_code=code_map.get(emp.id, ""),
            position_group=group_map.get(c.bhxh_position_group_id),
            resolved_grade_no=await _resolve_contract_read_grade_no(session, c),
        )
        for c, cat, emp in rows
    ]

    return ContractListPage(items=items, total=total, page=page, page_size=page_size)
