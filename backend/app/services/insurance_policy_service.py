from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.insurance import (
    InsuranceContributionComponent,
    InsurancePolicyComponentRate,
    InsurancePolicyVersion,
)
from app.models.salary import BhxhSenioritySetting, CompanyBhxhRegion, RegionalMinimumWage
from app.schemas.insurance import (
    BhxhSenioritySettingCreate,
    BhxhSenioritySettingsRead,
    BhxhSenioritySettingUpdate,
    CompanyRegionUpsert,
    RegionalMinimumWageCreate,
    RegionalMinimumWageRead,
    RegionalMinimumWageUpdate,
    InsurancePolicyComponentRateInput,
    InsurancePolicyVersionCreate,
    InsurancePolicyVersionUpdate,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _minimum_wage_to_read(item: RegionalMinimumWage) -> dict:
    return {
        "id": item.id,
        "decree_number": item.decree_number,
        "region": item.region,
        "amount": int(item.amount),
        "effective_from": item.effective_from,
        "effective_to": item.effective_to,
        "note": item.note,
    }


def _seniority_to_read(item: BhxhSenioritySetting) -> dict:
    return {
        "id": item.id,
        "raise_month": item.raise_month,
        "raise_day": item.raise_day,
        "years_per_grade": item.years_per_grade,
        "first_year_cutoff_month": item.first_year_cutoff_month,
        "first_year_cutoff_day": item.first_year_cutoff_day,
        "effective_from": item.effective_from,
        "effective_to": item.effective_to,
        "note": item.note,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _validate_complete_component_set(
    active_components: list[InsuranceContributionComponent],
    inputs: Iterable[InsurancePolicyComponentRateInput],
) -> None:
    items = list(inputs)
    input_codes = [item.component_code for item in items]
    duplicate_codes = sorted({code for code in input_codes if input_codes.count(code) > 1})
    if duplicate_codes:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Component bị lặp: {', '.join(duplicate_codes)}",
        )

    expected = {component.code for component in active_components}
    actual = set(input_codes)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        parts: list[str] = []
        if missing:
            parts.append(f"thiếu component: {', '.join(missing)}")
        if extra:
            parts.append(f"component không hợp lệ: {', '.join(extra)}")
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Bộ component không đầy đủ, {'; '.join(parts)}",
        )


async def list_components(session: AsyncSession) -> list[InsuranceContributionComponent]:
    rows = await session.execute(
        select(InsuranceContributionComponent).order_by(
            InsuranceContributionComponent.sort_order,
            InsuranceContributionComponent.code,
        )
    )
    return list(rows.scalars().all())


def _rate_to_read(rate: InsurancePolicyComponentRate, component: InsuranceContributionComponent) -> dict:
    return {
        "id": rate.id,
        "component_code": rate.component_code,
        "component_name": component.name_vi,
        "insurance_kind": component.insurance_kind,
        "sort_order": component.sort_order,
        "employee_rate_percent": Decimal(str(rate.employee_rate_percent)),
        "employer_rate_percent": Decimal(str(rate.employer_rate_percent)),
        "employer_advances_employee_part": rate.employer_advances_employee_part,
        "is_active": rate.is_active,
    }


async def _get_component_map(session: AsyncSession) -> dict[str, InsuranceContributionComponent]:
    components = await list_components(session)
    return {component.code: component for component in components}


async def _get_policy_or_404(session: AsyncSession, policy_id: int) -> InsurancePolicyVersion:
    policy = await session.get(InsurancePolicyVersion, policy_id)
    if not policy:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy policy version")
    return policy


async def _policy_to_read(session: AsyncSession, policy: InsurancePolicyVersion) -> dict:
    component_map = await _get_component_map(session)
    rate_rows = await session.execute(
        select(InsurancePolicyComponentRate)
        .where(InsurancePolicyComponentRate.policy_version_id == policy.id)
        .order_by(InsurancePolicyComponentRate.component_code)
    )
    rates = []
    for rate in rate_rows.scalars().all():
        component = component_map.get(rate.component_code)
        if component:
            rates.append(_rate_to_read(rate, component))
    rates.sort(key=lambda item: (item["sort_order"], item["component_code"]))
    return {
        "id": policy.id,
        "code": policy.code,
        "name": policy.name,
        "legal_basis_summary": policy.legal_basis_summary,
        "effective_from": policy.effective_from,
        "effective_to": policy.effective_to,
        "is_active": policy.is_active,
        "company_region": policy.company_region,
        "note": policy.note,
        "components": rates,
        "created_at": policy.created_at,
        "updated_at": policy.updated_at,
    }


async def list_policy_versions(session: AsyncSession) -> list[dict]:
    rows = await session.execute(
        select(InsurancePolicyVersion).order_by(
            InsurancePolicyVersion.effective_from.desc(),
            InsurancePolicyVersion.id.desc(),
        )
    )
    policies = list(rows.scalars().all())
    return [await _policy_to_read(session, policy) for policy in policies]


async def create_policy_version(session: AsyncSession, payload: InsurancePolicyVersionCreate) -> dict:
    existing = await session.execute(
        select(InsurancePolicyVersion).where(InsurancePolicyVersion.code == payload.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Policy code '{payload.code}' đã tồn tại")

    components = [item for item in await list_components(session) if item.is_active]
    _validate_complete_component_set(components, payload.components)

    policy = InsurancePolicyVersion(
        code=payload.code,
        name=payload.name,
        legal_basis_summary=payload.legal_basis_summary,
        effective_from=payload.effective_from,
        company_region=payload.company_region,
        note=payload.note,
        is_active=False,
    )
    session.add(policy)
    await session.flush()

    for item in payload.components:
        session.add(
            InsurancePolicyComponentRate(
                policy_version_id=policy.id,
                component_code=item.component_code,
                employee_rate_percent=float(item.employee_rate_percent),
                employer_rate_percent=float(item.employer_rate_percent),
                employer_advances_employee_part=item.employer_advances_employee_part,
                is_active=True,
            )
        )

    await session.commit()
    await session.refresh(policy)
    return await _policy_to_read(session, policy)


async def update_policy_version(session: AsyncSession, policy_id: int, payload: InsurancePolicyVersionUpdate) -> dict:
    policy = await _get_policy_or_404(session, policy_id)
    if policy.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Không thể sửa policy đang active")
    if policy.effective_to is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Không thể sửa policy lịch sử")

    provided = payload.model_fields_set
    if "name" in provided and payload.name is not None:
        policy.name = payload.name
    if "legal_basis_summary" in provided:
        policy.legal_basis_summary = payload.legal_basis_summary
    if "effective_from" in provided and payload.effective_from is not None:
        policy.effective_from = payload.effective_from
    if "company_region" in provided and payload.company_region is not None:
        policy.company_region = payload.company_region
    if "note" in provided:
        policy.note = payload.note
    policy.updated_at = _utcnow()

    if "components" in provided and payload.components is not None:
        components = [item for item in await list_components(session) if item.is_active]
        _validate_complete_component_set(components, payload.components)
        current_rows = await session.execute(
            select(InsurancePolicyComponentRate).where(InsurancePolicyComponentRate.policy_version_id == policy.id)
        )
        current_map = {row.component_code: row for row in current_rows.scalars().all()}
        for item in payload.components:
            row = current_map[item.component_code]
            row.employee_rate_percent = float(item.employee_rate_percent)
            row.employer_rate_percent = float(item.employer_rate_percent)
            row.employer_advances_employee_part = item.employer_advances_employee_part

    await session.commit()
    await session.refresh(policy)
    return await _policy_to_read(session, policy)


async def activate_policy_version(session: AsyncSession, policy_id: int) -> dict:
    policy = await _get_policy_or_404(session, policy_id)
    if policy.is_active:
        return await _policy_to_read(session, policy)

    components = [item for item in await list_components(session) if item.is_active]
    current_rates = await session.execute(
        select(InsurancePolicyComponentRate).where(InsurancePolicyComponentRate.policy_version_id == policy.id)
    )
    _validate_complete_component_set(
        components,
        [
            InsurancePolicyComponentRateInput(
                component_code=row.component_code,
                employee_rate_percent=Decimal(str(row.employee_rate_percent)),
                employer_rate_percent=Decimal(str(row.employer_rate_percent)),
                employer_advances_employee_part=row.employer_advances_employee_part,
            )
            for row in current_rates.scalars().all()
        ],
    )

    current_region = await get_company_region(session)
    if not current_region["current"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Chưa có vùng BHXH công ty đang hiệu lực")
    if current_region["current"]["region"] != policy.company_region:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Company region của policy không khớp với vùng BHXH công ty hiện hành",
        )

    active_stmt = select(InsurancePolicyVersion).where(InsurancePolicyVersion.is_active.is_(True))
    active = (await session.execute(active_stmt)).scalar_one_or_none()
    if active:
        if policy.effective_from <= active.effective_from:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ngày hiệu lực policy mới phải lớn hơn policy đang active",
            )
        active.is_active = False
        active.effective_to = policy.effective_from - timedelta(days=1)
        active.updated_at = _utcnow()

    policy.is_active = True
    policy.effective_to = None
    policy.updated_at = _utcnow()
    await session.commit()
    await session.refresh(policy)
    return await _policy_to_read(session, policy)


async def delete_policy_version(session: AsyncSession, policy_id: int) -> None:
    policy = await _get_policy_or_404(session, policy_id)
    if policy.is_active or policy.effective_to is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ được hủy policy ở trạng thái nháp chưa từng active",
        )

    await session.delete(policy)
    await session.commit()


async def get_company_region(session: AsyncSession) -> dict:
    rows = await session.execute(
        select(CompanyBhxhRegion).order_by(
            CompanyBhxhRegion.effective_from.desc(),
            CompanyBhxhRegion.id.desc(),
        )
    )
    items = list(rows.scalars().all())
    history = [
        {
            "id": item.id,
            "region": item.region,
            "effective_from": item.effective_from,
            "effective_to": item.effective_to,
            "note": item.note,
        }
        for item in items
    ]
    current = next((item for item in history if item["effective_to"] is None), None)
    return {"current": current, "history": history}


async def resolve_company_region_for_date(session: AsyncSession, *, as_of_date: date) -> CompanyBhxhRegion:
    rows = await session.execute(
        select(CompanyBhxhRegion).where(
            CompanyBhxhRegion.effective_from <= as_of_date,
            or_(
                CompanyBhxhRegion.effective_to.is_(None),
                CompanyBhxhRegion.effective_to >= as_of_date,
            ),
        )
    )
    matches = list(rows.scalars().all())
    if not matches:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Không có vùng BHXH công ty hiệu lực cho ngày {as_of_date.isoformat()}",
        )
    if len(matches) > 1:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Phát hiện nhiều vùng BHXH công ty cùng hiệu lực cho ngày {as_of_date.isoformat()}",
        )
    return matches[0]


async def resolve_policy_version_for_date(session: AsyncSession, *, as_of_date: date) -> InsurancePolicyVersion:
    rows = await session.execute(
        select(InsurancePolicyVersion).where(
            InsurancePolicyVersion.effective_from <= as_of_date,
            or_(
                InsurancePolicyVersion.effective_to.is_(None),
                InsurancePolicyVersion.effective_to >= as_of_date,
            ),
            or_(
                InsurancePolicyVersion.is_active.is_(True),
                InsurancePolicyVersion.effective_to.is_not(None),
            ),
        )
    )
    matches = list(rows.scalars().all())
    if not matches:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Không có policy version hiệu lực cho ngày {as_of_date.isoformat()}",
        )
    if len(matches) > 1:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Phát hiện nhiều policy version cùng hiệu lực cho ngày {as_of_date.isoformat()}",
        )
    return matches[0]


async def resolve_effective_contribution_config(
    session: AsyncSession,
    *,
    as_of_date: date,
) -> dict:
    company_region = await resolve_company_region_for_date(session, as_of_date=as_of_date)
    policy = await resolve_policy_version_for_date(session, as_of_date=as_of_date)

    if policy.company_region != company_region.region:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=(
                "Policy version hiệu lực không khớp với vùng BHXH công ty "
                f"cho ngày {as_of_date.isoformat()}"
            ),
        )

    components = [item for item in await list_components(session) if item.is_active]
    current_rates = await session.execute(
        select(InsurancePolicyComponentRate).where(
            InsurancePolicyComponentRate.policy_version_id == policy.id
        )
    )
    _validate_complete_component_set(
        components,
        [
            InsurancePolicyComponentRateInput(
                component_code=row.component_code,
                employee_rate_percent=Decimal(str(row.employee_rate_percent)),
                employer_rate_percent=Decimal(str(row.employer_rate_percent)),
                employer_advances_employee_part=row.employer_advances_employee_part,
            )
            for row in current_rates.scalars().all()
        ],
    )

    return {
        "as_of_date": as_of_date,
        "company_region": {
            "id": company_region.id,
            "region": company_region.region,
            "effective_from": company_region.effective_from,
            "effective_to": company_region.effective_to,
            "note": company_region.note,
        },
        "policy_version": await _policy_to_read(session, policy),
    }


async def upsert_company_region(session: AsyncSession, payload: CompanyRegionUpsert) -> dict:
    rows = await session.execute(
        select(CompanyBhxhRegion).where(CompanyBhxhRegion.effective_to.is_(None))
    )
    current = rows.scalar_one_or_none()
    if current:
        if payload.effective_from <= current.effective_from:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Ngày hiệu lực vùng mới phải lớn hơn vùng đang hiệu lực",
            )
        current.effective_to = payload.effective_from - timedelta(days=1)

    new_row = CompanyBhxhRegion(
        region=payload.region,
        effective_from=payload.effective_from,
        effective_to=None,
        note=payload.note,
    )
    session.add(new_row)
    await session.commit()
    return await get_company_region(session)


async def list_minimum_wages(session: AsyncSession) -> list[dict]:
    rows = await session.execute(
        select(RegionalMinimumWage).order_by(
            RegionalMinimumWage.region.asc(),
            RegionalMinimumWage.effective_from.desc(),
            RegionalMinimumWage.id.desc(),
        )
    )
    return [_minimum_wage_to_read(item) for item in rows.scalars().all()]


async def create_minimum_wage(session: AsyncSession, payload: RegionalMinimumWageCreate) -> dict:
    rows = await session.execute(
        select(RegionalMinimumWage)
        .where(
            RegionalMinimumWage.region == payload.region,
            RegionalMinimumWage.effective_to.is_(None),
        )
        .order_by(RegionalMinimumWage.effective_from.desc(), RegionalMinimumWage.id.desc())
    )
    current = rows.scalars().first()
    if current and payload.effective_from <= current.effective_from:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Ngày hiệu lực LTTV mới phải lớn hơn cấu hình đang hiệu lực của cùng vùng",
        )

    if current:
        current.effective_to = payload.effective_from - timedelta(days=1)

    new_row = RegionalMinimumWage(
        decree_number=payload.decree_number,
        region=payload.region,
        amount=payload.amount,
        effective_from=payload.effective_from,
        effective_to=None,
        note=payload.note,
    )
    session.add(new_row)
    await session.commit()
    await session.refresh(new_row)
    return _minimum_wage_to_read(new_row)


async def update_minimum_wage(
    session: AsyncSession,
    wage_id: int,
    payload: RegionalMinimumWageUpdate,
) -> dict:
    row = await session.get(RegionalMinimumWage, wage_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cấu hình lương tối thiểu vùng")

    provided = payload.model_fields_set
    if "decree_number" in provided and payload.decree_number is not None:
        row.decree_number = payload.decree_number
    if "amount" in provided and payload.amount is not None:
        row.amount = payload.amount
    if "note" in provided:
        row.note = payload.note

    session.add(row)
    await session.commit()
    await session.refresh(row)
    return _minimum_wage_to_read(row)


async def delete_minimum_wage(session: AsyncSession, wage_id: int) -> None:
    row = await session.get(RegionalMinimumWage, wage_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cấu hình lương tối thiểu vùng")

    rows = await session.execute(
        select(RegionalMinimumWage)
        .where(RegionalMinimumWage.region == row.region)
        .order_by(RegionalMinimumWage.effective_from.asc(), RegionalMinimumWage.id.asc())
    )
    region_items = list(rows.scalars().all())
    idx = next((i for i, item in enumerate(region_items) if item.id == row.id), None)
    if idx is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cấu hình lương tối thiểu vùng")

    previous = region_items[idx - 1] if idx > 0 else None
    following = region_items[idx + 1] if idx + 1 < len(region_items) else None

    if previous:
        previous.effective_to = (following.effective_from - timedelta(days=1)) if following else None
        session.add(previous)

    await session.delete(row)
    await session.commit()


async def get_bhxh_seniority_settings(session: AsyncSession) -> dict:
    rows = await session.execute(
        select(BhxhSenioritySetting).order_by(
            BhxhSenioritySetting.effective_from.desc(),
            BhxhSenioritySetting.id.desc(),
        )
    )
    items = list(rows.scalars().all())
    history = [_seniority_to_read(item) for item in items]
    current = next((item for item in history if item["effective_to"] is None), None)
    return {"current": current, "history": history}


async def create_bhxh_seniority_setting(
    session: AsyncSession,
    payload: BhxhSenioritySettingCreate,
) -> dict:
    rows = await session.execute(
        select(BhxhSenioritySetting)
        .where(BhxhSenioritySetting.effective_to.is_(None))
        .order_by(BhxhSenioritySetting.effective_from.desc(), BhxhSenioritySetting.id.desc())
    )
    current = rows.scalars().first()
    if current and payload.effective_from <= current.effective_from:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Ngày hiệu lực rule thâm niên mới phải lớn hơn rule đang hiệu lực",
        )

    if current:
        current.effective_to = payload.effective_from - timedelta(days=1)
        current.updated_at = _utcnow()

    new_row = BhxhSenioritySetting(
        raise_month=payload.raise_month,
        raise_day=payload.raise_day,
        years_per_grade=payload.years_per_grade,
        first_year_cutoff_month=payload.first_year_cutoff_month,
        first_year_cutoff_day=payload.first_year_cutoff_day,
        effective_from=payload.effective_from,
        effective_to=None,
        note=payload.note,
    )
    session.add(new_row)
    await session.commit()
    return await get_bhxh_seniority_settings(session)


async def update_bhxh_seniority_setting(
    session: AsyncSession,
    setting_id: int,
    payload: BhxhSenioritySettingUpdate,
) -> dict:
    row = await session.get(BhxhSenioritySetting, setting_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cấu hình rule thâm niên")

    provided = payload.model_fields_set
    if "raise_month" in provided and payload.raise_month is not None:
        row.raise_month = payload.raise_month
    if "raise_day" in provided and payload.raise_day is not None:
        row.raise_day = payload.raise_day
    if "years_per_grade" in provided and payload.years_per_grade is not None:
        row.years_per_grade = payload.years_per_grade
    if "first_year_cutoff_month" in provided and payload.first_year_cutoff_month is not None:
        row.first_year_cutoff_month = payload.first_year_cutoff_month
    if "first_year_cutoff_day" in provided and payload.first_year_cutoff_day is not None:
        row.first_year_cutoff_day = payload.first_year_cutoff_day
    if "note" in provided:
        row.note = payload.note
    row.updated_at = _utcnow()

    session.add(row)
    await session.commit()
    return await get_bhxh_seniority_settings(session)


async def delete_bhxh_seniority_setting(session: AsyncSession, setting_id: int) -> dict:
    row = await session.get(BhxhSenioritySetting, setting_id)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cấu hình rule thâm niên")

    rows = await session.execute(
        select(BhxhSenioritySetting).order_by(
            BhxhSenioritySetting.effective_from.asc(),
            BhxhSenioritySetting.id.asc(),
        )
    )
    items = list(rows.scalars().all())
    idx = next((i for i, item in enumerate(items) if item.id == row.id), None)
    if idx is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy cấu hình rule thâm niên")

    previous = items[idx - 1] if idx > 0 else None
    following = items[idx + 1] if idx + 1 < len(items) else None

    if previous:
        previous.effective_to = (following.effective_from - timedelta(days=1)) if following else None
        previous.updated_at = _utcnow()
        session.add(previous)

    await session.delete(row)
    await session.commit()
    return await get_bhxh_seniority_settings(session)
