from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.employee_insurance import (
    EmployeeInsuranceListPage,
    EmployeeInsuranceProfileRead,
    EmployeeInsuranceProfileUpdate,
)
from app.schemas.insurance import (
    CompanyRegionRead,
    CompanyRegionUpsert,
    InsuranceEffectiveContributionConfigRead,
    InsuranceContributionComponentRead,
    InsurancePolicyVersionCreate,
    InsurancePolicyVersionRead,
    InsurancePolicyVersionUpdate,
)
from app.schemas.insurance_change import (
    InsuranceChangeEventCreate,
    InsuranceChangeEventListPage,
    InsuranceChangeEventRead,
    InsuranceMonthlyChangeSummary,
)
from app.services import employee_insurance_service, insurance_change_service, insurance_policy_service

router = APIRouter()


@router.get("/components", response_model=list[InsuranceContributionComponentRead], summary="Danh sách component đóng BHXH/BHYT/BHTN")
async def list_insurance_components(
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await insurance_policy_service.list_components(session)


@router.get("/policy-versions", response_model=list[InsurancePolicyVersionRead], summary="Danh sách policy version bảo hiểm")
async def list_insurance_policy_versions(
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await insurance_policy_service.list_policy_versions(session)


@router.post("/policy-versions", response_model=InsurancePolicyVersionRead, status_code=status.HTTP_201_CREATED, summary="Tạo policy version mới")
async def create_insurance_policy_version(
    body: InsurancePolicyVersionCreate,
    _: User = require_permission("insurance:create"),
    session: AsyncSession = Depends(get_session),
):
    return await insurance_policy_service.create_policy_version(session, body)


@router.put("/policy-versions/{policy_id}", response_model=InsurancePolicyVersionRead, summary="Cập nhật policy version chưa active")
async def update_insurance_policy_version(
    policy_id: int,
    body: InsurancePolicyVersionUpdate,
    _: User = require_permission("insurance:edit"),
    session: AsyncSession = Depends(get_session),
):
    return await insurance_policy_service.update_policy_version(session, policy_id, body)


@router.post("/policy-versions/{policy_id}/activate", response_model=InsurancePolicyVersionRead, summary="Activate policy version")
async def activate_insurance_policy_version(
    policy_id: int,
    _: User = require_permission("insurance:edit"),
    session: AsyncSession = Depends(get_session),
):
    return await insurance_policy_service.activate_policy_version(session, policy_id)


@router.delete("/policy-versions/{policy_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Hủy nháp policy version chưa active")
async def delete_insurance_policy_version(
    policy_id: int,
    _: User = require_permission("insurance:delete"),
    session: AsyncSession = Depends(get_session),
):
    await insurance_policy_service.delete_policy_version(session, policy_id)


@router.get("/company-region", response_model=CompanyRegionRead, summary="Xem vùng BHXH công ty hiện hành và lịch sử")
async def get_company_bhxh_region(
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await insurance_policy_service.get_company_region(session)


@router.get(
    "/effective-config",
    response_model=InsuranceEffectiveContributionConfigRead,
    summary="Resolve cấu hình đóng BHXH/BHYT/BHTN hiệu lực theo ngày",
)
async def get_effective_contribution_config(
    as_of_date: date = Query(..., description="Ngày cần resolve cấu hình hiệu lực"),
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await insurance_policy_service.resolve_effective_contribution_config(
        session,
        as_of_date=as_of_date,
    )


@router.put("/company-region", response_model=CompanyRegionRead, summary="Cập nhật vùng BHXH công ty")
async def update_company_bhxh_region(
    body: CompanyRegionUpsert,
    _: User = require_permission("insurance:edit"),
    session: AsyncSession = Depends(get_session),
):
    return await insurance_policy_service.upsert_company_region(session, body)


# ── Employee insurance profile endpoints ──────────────────────────────────────

@router.get(
    "/employees",
    response_model=EmployeeInsuranceListPage,
    summary="Danh sách hồ sơ bảo hiểm nhân viên",
)
async def list_employee_insurance_profiles(
    keyword: str | None = Query(None, description="Tìm theo mã NV, tên, mã BHXH"),
    department_id: int | None = Query(None),
    participation_status: str | None = Query(None, description="active | paused | stopped"),
    has_bhxh_code: bool | None = Query(None),
    joined_from: date | None = Query(None),
    joined_to: date | None = Query(None),
    policy_version_id: int | None = Query(None),
    has_component_overrides: bool | None = Query(None),
    employer_pays_on_behalf: bool | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await employee_insurance_service.list_insurance_profiles(
        session,
        keyword=keyword,
        department_id=department_id,
        participation_status=participation_status,
        has_bhxh_code=has_bhxh_code,
        joined_from=joined_from,
        joined_to=joined_to,
        policy_version_id=policy_version_id,
        has_component_overrides=has_component_overrides,
        employer_pays_on_behalf=employer_pays_on_behalf,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/employees/{employee_id}",
    response_model=EmployeeInsuranceProfileRead,
    summary="Chi tiết hồ sơ bảo hiểm của 1 nhân viên",
)
async def get_employee_insurance_profile(
    employee_id: int,
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await employee_insurance_service.get_insurance_profile_detail(session, employee_id)


@router.put(
    "/employees/{employee_id}",
    response_model=EmployeeInsuranceProfileRead,
    summary="Cập nhật hồ sơ bảo hiểm + overrides của nhân viên",
)
async def upsert_employee_insurance_profile(
    employee_id: int,
    body: EmployeeInsuranceProfileUpdate,
    _: User = require_permission("insurance:edit"),
    session: AsyncSession = Depends(get_session),
):
    return await employee_insurance_service.upsert_insurance_profile(session, employee_id, body)


# ── Change Events ──────────────────────────────────────────────────────────────

@router.get(
    "/change-events",
    response_model=InsuranceChangeEventListPage,
    summary="Danh sách biến động tăng/giảm BHXH",
)
async def list_insurance_change_events(
    employee_id: Optional[int] = Query(None),
    change_type: Optional[str] = Query(None, pattern=r"^(increase|decrease)$"),
    period_year: Optional[int] = Query(None),
    period_month: Optional[int] = Query(None, ge=1, le=12),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await insurance_change_service.list_change_events(
        session,
        employee_id=employee_id,
        change_type=change_type,
        period_year=period_year,
        period_month=period_month,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/change-events/monthly-summary",
    response_model=InsuranceMonthlyChangeSummary,
    summary="Tổng hợp tăng/giảm BHXH theo tháng",
)
async def get_insurance_monthly_summary(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    _: User = require_permission("insurance:view"),
    session: AsyncSession = Depends(get_session),
):
    return await insurance_change_service.get_monthly_summary(session, year, month)


@router.post(
    "/change-events",
    response_model=InsuranceChangeEventRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo biến động thủ công",
)
async def create_manual_insurance_change_event(
    body: InsuranceChangeEventCreate,
    current_user: User = require_permission("insurance:edit"),
    session: AsyncSession = Depends(get_session),
):
    return await insurance_change_service.create_manual_event(
        session, body, created_by_id=current_user.id
    )


@router.delete(
    "/change-events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa biến động thủ công",
)
async def delete_manual_insurance_change_event(
    event_id: int,
    _: User = require_permission("insurance:edit"),
    session: AsyncSession = Depends(get_session),
):
    await insurance_change_service.delete_manual_event(session, event_id)
