"""Endpoints tuyển dụng ATS — 13.1 Kế hoạch & Yêu cầu tuyển dụng / 13.2 Đăng tin."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.recruitment import (
    BudgetItemCreate,
    BudgetItemRead,
    BudgetItemUpdate,
    BudgetSummary,
    CancelRequest,
    HeadcountPlanCreate,
    HeadcountPlanListPage,
    HeadcountPlanRead,
    HeadcountPlanUpdate,
    JobPostingCreate,
    JobPostingListPage,
    JobPostingRead,
    JobPostingUpdate,
    JobRequisitionCreate,
    JobRequisitionListPage,
    JobRequisitionRead,
    JobRequisitionUpdate,
    LanguageValidationRequest,
    LanguageValidationResult,
    RecruitmentChannelCreate,
    RecruitmentChannelRead,
    RecruitmentChannelUpdate,
    RejectRequest,
)
from app.services import auth_service, headcount_plan_service, jr_service, job_posting_service

router = APIRouter()

_TAG = "Tuyển dụng"


# ── Headcount Plan ────────────────────────────────────────────────────────────


@router.get(
    "/headcount-plans",
    response_model=HeadcountPlanListPage,
    tags=[_TAG],
    summary="Danh sách kế hoạch nhân sự",
)
async def list_headcount_plans(
    year: Optional[int] = Query(None, ge=2000, le=2100),
    department_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await headcount_plan_service.list_headcount_plans(
        session, year=year, department_id=department_id, page=page, page_size=page_size
    )


@router.get(
    "/headcount-plans/fulfillment",
    tags=[_TAG],
    summary="Tỷ lệ hoàn thành kế hoạch nhân sự",
)
async def get_fulfillment_rate(
    year: int = Query(..., ge=2000, le=2100),
    department_id: Optional[int] = Query(None),
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await headcount_plan_service.get_fulfillment_rate(session, year, department_id)


@router.get(
    "/headcount-plans/{plan_id}",
    response_model=HeadcountPlanRead,
    tags=[_TAG],
    summary="Chi tiết kế hoạch nhân sự",
)
async def get_headcount_plan(
    plan_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await headcount_plan_service.get_headcount_plan(session, plan_id)


@router.post(
    "/headcount-plans",
    response_model=HeadcountPlanRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Tạo kế hoạch nhân sự",
)
async def create_headcount_plan(
    body: HeadcountPlanCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await headcount_plan_service.create_headcount_plan(session, body, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="headcount_plan", entity_id=result.id,
        entity_name=f"Năm {result.year} — {result.department_name or 'Toàn công ty'}",
    )
    await session.commit()
    return result


@router.put(
    "/headcount-plans/{plan_id}",
    response_model=HeadcountPlanRead,
    tags=[_TAG],
    summary="Cập nhật kế hoạch nhân sự",
)
async def update_headcount_plan(
    plan_id: int,
    body: HeadcountPlanUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await headcount_plan_service.update_headcount_plan(session, plan_id, body)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="headcount_plan", entity_id=plan_id,
        entity_name=str(plan_id),
    )
    await session.commit()
    return result


@router.delete(
    "/headcount-plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
    summary="Xóa kế hoạch nhân sự",
)
async def delete_headcount_plan(
    plan_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await headcount_plan_service.delete_headcount_plan(session, plan_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="headcount_plan", entity_id=plan_id,
        entity_name=str(plan_id),
    )
    await session.commit()


# ── Job Requisition — List / Get ──────────────────────────────────────────────


@router.get(
    "/job-requisitions",
    response_model=JobRequisitionListPage,
    tags=[_TAG],
    summary="Danh sách yêu cầu tuyển dụng (phân trang + filter)",
)
async def list_job_requisitions(
    status: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    job_position_id: Optional[int] = Query(None),
    year: Optional[int] = Query(None, ge=2000, le=2100),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await jr_service.list_job_requisitions(
        session,
        status=status,
        department_id=department_id,
        job_position_id=job_position_id,
        year=year,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/job-requisitions/{jr_id}",
    response_model=JobRequisitionRead,
    tags=[_TAG],
    summary="Chi tiết yêu cầu tuyển dụng",
)
async def get_job_requisition(
    jr_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await jr_service.get_job_requisition(session, jr_id)


# ── Job Requisition — Create / Update / Delete ────────────────────────────────


@router.post(
    "/job-requisitions",
    response_model=JobRequisitionRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Tạo yêu cầu tuyển dụng",
)
async def create_job_requisition(
    body: JobRequisitionCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await jr_service.create_job_requisition(session, body, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="job_requisition", entity_id=result.id,
        entity_name=result.code,
    )
    await session.commit()
    return result


@router.put(
    "/job-requisitions/{jr_id}",
    response_model=JobRequisitionRead,
    tags=[_TAG],
    summary="Sửa yêu cầu tuyển dụng (chỉ khi draft/pending_review)",
)
async def update_job_requisition(
    jr_id: int,
    body: JobRequisitionUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await jr_service.update_job_requisition(session, jr_id, body)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="job_requisition", entity_id=jr_id,
        entity_name=result.code,
    )
    await session.commit()
    return result


@router.delete(
    "/job-requisitions/{jr_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
    summary="Xóa yêu cầu tuyển dụng (chỉ khi status=draft)",
)
async def delete_job_requisition(
    jr_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await jr_service.delete_job_requisition(session, jr_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="job_requisition", entity_id=jr_id,
        entity_name=str(jr_id),
    )
    await session.commit()


# ── Job Requisition — Workflow ────────────────────────────────────────────────


@router.post(
    "/job-requisitions/{jr_id}/submit",
    response_model=JobRequisitionRead,
    tags=[_TAG],
    summary="Gửi duyệt yêu cầu tuyển dụng (draft → pending_review)",
)
async def submit_job_requisition(
    jr_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await jr_service.submit_job_requisition(session, jr_id, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="job_requisition", entity_id=jr_id,
        entity_name=f"{result.code} → pending_review",
    )
    await session.commit()
    return result


@router.post(
    "/job-requisitions/{jr_id}/approve",
    response_model=JobRequisitionRead,
    tags=[_TAG],
    summary="Duyệt yêu cầu tuyển dụng (pending_review → approved)",
)
async def approve_job_requisition(
    jr_id: int,
    current_user: User = require_permission("recruitment:approve"),
    session: AsyncSession = Depends(get_session),
):
    result = await jr_service.approve_job_requisition(session, jr_id, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="job_requisition", entity_id=jr_id,
        entity_name=f"{result.code} → approved",
    )
    await session.commit()
    return result


@router.post(
    "/job-requisitions/{jr_id}/reject",
    response_model=JobRequisitionRead,
    tags=[_TAG],
    summary="Từ chối yêu cầu tuyển dụng (pending_review → draft)",
)
async def reject_job_requisition(
    jr_id: int,
    body: RejectRequest,
    current_user: User = require_permission("recruitment:approve"),
    session: AsyncSession = Depends(get_session),
):
    result = await jr_service.reject_job_requisition(session, jr_id, current_user.id, body)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="job_requisition", entity_id=jr_id,
        entity_name=f"{result.code} → rejected",
    )
    await session.commit()
    return result


@router.post(
    "/job-requisitions/{jr_id}/cancel",
    response_model=JobRequisitionRead,
    tags=[_TAG],
    summary="Hủy yêu cầu tuyển dụng",
)
async def cancel_job_requisition(
    jr_id: int,
    body: CancelRequest,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await jr_service.cancel_job_requisition(session, jr_id, current_user.id, body)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="job_requisition", entity_id=jr_id,
        entity_name=f"{result.code} → cancelled",
    )
    await session.commit()
    return result


# ── Budget ────────────────────────────────────────────────────────────────────


@router.get(
    "/job-requisitions/{jr_id}/budget",
    response_model=BudgetSummary,
    tags=[_TAG],
    summary="Danh sách chi phí tuyển dụng của JR",
)
async def get_budget_summary(
    jr_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await jr_service.get_budget_summary(session, jr_id)


@router.post(
    "/job-requisitions/{jr_id}/budget",
    response_model=BudgetItemRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Thêm khoản chi phí tuyển dụng",
)
async def add_budget_item(
    jr_id: int,
    body: BudgetItemCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await jr_service.add_budget_item(session, jr_id, body, current_user.id)
    await session.commit()
    return result


@router.put(
    "/job-requisitions/{jr_id}/budget/{item_id}",
    response_model=BudgetItemRead,
    tags=[_TAG],
    summary="Cập nhật khoản chi phí tuyển dụng",
)
async def update_budget_item(
    jr_id: int,
    item_id: int,
    body: BudgetItemUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await jr_service.update_budget_item(session, jr_id, item_id, body)
    await session.commit()
    return result


@router.delete(
    "/job-requisitions/{jr_id}/budget/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
    summary="Xóa khoản chi phí tuyển dụng",
)
async def delete_budget_item(
    jr_id: int,
    item_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await jr_service.delete_budget_item(session, jr_id, item_id)
    await session.commit()


# ── Recruitment Channels ──────────────────────────────────────────────────────


@router.get(
    "/channels",
    response_model=List[RecruitmentChannelRead],
    tags=[_TAG],
    summary="Danh sách kênh tuyển dụng",
)
async def list_channels(
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await job_posting_service.list_channels(session)


@router.post(
    "/channels",
    response_model=RecruitmentChannelRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Thêm kênh tuyển dụng",
)
async def create_channel(
    body: RecruitmentChannelCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await job_posting_service.create_channel(session, body)
    await session.commit()
    return result


@router.put(
    "/channels/{channel_id}",
    response_model=RecruitmentChannelRead,
    tags=[_TAG],
    summary="Cập nhật kênh tuyển dụng",
)
async def update_channel(
    channel_id: int,
    body: RecruitmentChannelUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await job_posting_service.update_channel(session, channel_id, body)
    await session.commit()
    return result


@router.delete(
    "/channels/{channel_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
    summary="Xóa kênh tuyển dụng",
)
async def delete_channel(
    channel_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await job_posting_service.delete_channel(session, channel_id)
    await session.commit()


# ── Job Postings ──────────────────────────────────────────────────────────────


@router.get(
    "/job-postings",
    response_model=JobPostingListPage,
    tags=[_TAG],
    summary="Danh sách tin tuyển dụng",
)
async def list_job_postings(
    status: Optional[str] = Query(None),
    job_requisition_id: Optional[int] = Query(None),
    posting_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await job_posting_service.list_postings(
        session,
        status=status,
        job_requisition_id=job_requisition_id,
        posting_type=posting_type,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/job-postings/validate-language",
    response_model=LanguageValidationResult,
    tags=[_TAG],
    summary="Kiểm tra ngôn ngữ phân biệt đối xử trong tin tuyển dụng",
)
async def validate_language(
    body: LanguageValidationRequest,
    _: User = require_permission("recruitment:manage"),
):
    return job_posting_service.validate_language(body.text)


@router.post(
    "/job-postings",
    response_model=JobPostingRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
    summary="Tạo tin tuyển dụng (từ JR đã duyệt)",
)
async def create_job_posting(
    body: JobPostingCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await job_posting_service.create_posting(session, body, current_user.id)
    await session.commit()
    return result


@router.get(
    "/job-postings/{posting_id}",
    response_model=JobPostingRead,
    tags=[_TAG],
    summary="Chi tiết tin tuyển dụng",
)
async def get_job_posting(
    posting_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await job_posting_service.get_posting(session, posting_id)


@router.put(
    "/job-postings/{posting_id}",
    response_model=JobPostingRead,
    tags=[_TAG],
    summary="Cập nhật tin tuyển dụng (chỉ khi draft/active)",
)
async def update_job_posting(
    posting_id: int,
    body: JobPostingUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await job_posting_service.update_posting(session, posting_id, body)
    await session.commit()
    return result


@router.post(
    "/job-postings/{posting_id}/publish",
    response_model=JobPostingRead,
    tags=[_TAG],
    summary="Đăng tin (draft → active)",
)
async def publish_job_posting(
    posting_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await job_posting_service.publish_posting(session, posting_id)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="job_posting", entity_id=posting_id,
        entity_name=f"posting#{posting_id} → active",
    )
    await session.commit()
    return result


@router.post(
    "/job-postings/{posting_id}/close",
    response_model=JobPostingRead,
    tags=[_TAG],
    summary="Đóng tin tuyển dụng (active → closed)",
)
async def close_job_posting(
    posting_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await job_posting_service.close_posting(session, posting_id)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="job_posting", entity_id=posting_id,
        entity_name=f"posting#{posting_id} → closed",
    )
    await session.commit()
    return result


@router.post(
    "/job-postings/{posting_id}/reopen",
    response_model=JobPostingRead,
    tags=[_TAG],
    summary="Mở lại tin tuyển dụng (closed → active)",
)
async def reopen_job_posting(
    posting_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await job_posting_service.reopen_posting(session, posting_id)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="job_posting", entity_id=posting_id,
        entity_name=f"posting#{posting_id} → active (reopened)",
    )
    await session.commit()
    return result
