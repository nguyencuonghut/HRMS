from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.insurance import (
    CompanyRegionRead,
    CompanyRegionUpsert,
    InsuranceEffectiveContributionConfigRead,
    InsuranceContributionComponentRead,
    InsurancePolicyVersionCreate,
    InsurancePolicyVersionRead,
    InsurancePolicyVersionUpdate,
)
from app.services import insurance_policy_service

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
