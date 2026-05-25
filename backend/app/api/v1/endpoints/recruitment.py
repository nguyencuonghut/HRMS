"""Endpoints tuyển dụng ATS — 13.1 Kế hoạch & Yêu cầu tuyển dụng / 13.2 Đăng tin / 13.3 Ứng viên."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.recruitment import (
    ApplicationCreate,
    ApplicationListPage,
    ApplicationRead,
    BudgetItemCreate,
    BudgetItemRead,
    BudgetItemUpdate,
    BudgetSummary,
    CancelRequest,
    CandidateAttachmentRead,
    CandidateCreate,
    CandidateDuplicateCheck,
    CandidateDuplicateCheckResult,
    CandidateEducationCreate,
    CandidateEducationRead,
    CandidateListPage,
    CandidateRead,
    CandidateSkillCreate,
    CandidateSkillRead,
    CandidateUpdate,
    CandidateWorkExpCreate,
    CandidateWorkExpRead,
    HeadcountPlanCreate,
    HeadcountPlanListPage,
    HeadcountPlanRead,
    HeadcountPlanUpdate,
    ImportResult,
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
from app.services import (
    auth_service,
    candidate_service,
    headcount_plan_service,
    job_posting_service,
    jr_service,
)

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


# ── Candidates (13.3) ─────────────────────────────────────────────────────────


@router.get("/candidates/import-template", tags=[_TAG])
async def candidate_import_template(
    current_user: User = require_permission("recruitment:view"),
):
    from app.services.candidate_import_service import generate_template
    from fastapi.responses import Response
    content = generate_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=candidate_import_template.xlsx"},
    )


@router.post("/candidates/import", response_model=ImportResult, tags=[_TAG])
async def import_candidates(
    file: UploadFile = File(...),
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    from app.services.candidate_import_service import import_candidates_excel
    content = await file.read()
    result = await import_candidates_excel(session, content, current_user.id)
    await session.commit()
    return result


@router.get("/candidates", response_model=CandidateListPage, tags=[_TAG])
async def list_candidates(
    search: Optional[str] = Query(default=None),
    source_channel_id: Optional[int] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await candidate_service.list_candidates(session, search, source_channel_id, page, page_size)


@router.post("/candidates/check-duplicates", response_model=CandidateDuplicateCheckResult, tags=[_TAG])
async def check_candidate_duplicates(
    data: CandidateDuplicateCheck,
    _: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    return await candidate_service.check_candidate_duplicates(session, data)


@router.post("/candidates", response_model=CandidateRead, status_code=status.HTTP_201_CREATED, tags=[_TAG])
async def create_candidate(
    data: CandidateCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await candidate_service.create_candidate(session, data, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="candidate", entity_id=result.id, entity_name=result.full_name,
    )
    await session.commit()
    return result


@router.get("/candidates/{candidate_id}", response_model=CandidateRead, tags=[_TAG])
async def get_candidate(
    candidate_id: int,
    current_user: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await candidate_service.get_candidate(session, candidate_id)


@router.put("/candidates/{candidate_id}", response_model=CandidateRead, tags=[_TAG])
async def update_candidate(
    candidate_id: int,
    data: CandidateUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await candidate_service.update_candidate(session, candidate_id, data)
    await auth_service.log_audit(
        session, current_user.id, "UPDATE",
        entity_type="candidate", entity_id=candidate_id, entity_name=result.full_name,
    )
    await session.commit()
    return result


@router.delete("/candidates/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT, tags=[_TAG])
async def delete_candidate(
    candidate_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await candidate_service.delete_candidate(session, candidate_id)
    await auth_service.log_audit(
        session, current_user.id, "DELETE",
        entity_type="candidate", entity_id=candidate_id, entity_name=f"candidate#{candidate_id}",
    )
    await session.commit()


# ── Candidate Education ───────────────────────────────────────────────────────


@router.post(
    "/candidates/{candidate_id}/educations",
    response_model=CandidateEducationRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
)
async def add_education(
    candidate_id: int,
    data: CandidateEducationCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await candidate_service.add_education(session, candidate_id, data)
    await session.commit()
    return result


@router.put(
    "/candidates/{candidate_id}/educations/{edu_id}",
    response_model=CandidateEducationRead,
    tags=[_TAG],
)
async def update_education(
    candidate_id: int,
    edu_id: int,
    data: CandidateEducationCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await candidate_service.update_education(session, candidate_id, edu_id, data)
    await session.commit()
    return result


@router.delete(
    "/candidates/{candidate_id}/educations/{edu_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
)
async def delete_education(
    candidate_id: int,
    edu_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await candidate_service.delete_education(session, candidate_id, edu_id)
    await session.commit()


# ── Candidate Work Experience ─────────────────────────────────────────────────


@router.post(
    "/candidates/{candidate_id}/work-experiences",
    response_model=CandidateWorkExpRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
)
async def add_work_experience(
    candidate_id: int,
    data: CandidateWorkExpCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await candidate_service.add_work_experience(session, candidate_id, data)
    await session.commit()
    return result


@router.put(
    "/candidates/{candidate_id}/work-experiences/{exp_id}",
    response_model=CandidateWorkExpRead,
    tags=[_TAG],
)
async def update_work_experience(
    candidate_id: int,
    exp_id: int,
    data: CandidateWorkExpCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await candidate_service.update_work_experience(session, candidate_id, exp_id, data)
    await session.commit()
    return result


@router.delete(
    "/candidates/{candidate_id}/work-experiences/{exp_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
)
async def delete_work_experience(
    candidate_id: int,
    exp_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await candidate_service.delete_work_experience(session, candidate_id, exp_id)
    await session.commit()


# ── Candidate Skills ──────────────────────────────────────────────────────────


@router.post(
    "/candidates/{candidate_id}/skills",
    response_model=CandidateSkillRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
)
async def add_skill(
    candidate_id: int,
    data: CandidateSkillCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await candidate_service.add_skill(session, candidate_id, data)
    await session.commit()
    return result


@router.delete(
    "/candidates/{candidate_id}/skills/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
)
async def delete_skill(
    candidate_id: int,
    skill_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await candidate_service.delete_skill(session, candidate_id, skill_id)
    await session.commit()


# ── Candidate Attachments ─────────────────────────────────────────────────────


@router.post(
    "/candidates/{candidate_id}/attachments",
    response_model=CandidateAttachmentRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
)
async def upload_attachment(
    candidate_id: int,
    attachment_type: str = Form(...),
    note: Optional[str] = Form(default=None),
    file: UploadFile = File(...),
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    from app.services.candidate_import_service import save_candidate_attachment
    result = await save_candidate_attachment(
        session, candidate_id, file, attachment_type, note, current_user.id
    )
    await session.commit()
    return result


@router.delete(
    "/candidates/{candidate_id}/attachments/{att_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=[_TAG],
)
async def delete_attachment(
    candidate_id: int,
    att_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    from app.services.candidate_import_service import delete_candidate_attachment
    await delete_candidate_attachment(session, candidate_id, att_id)
    await session.commit()


@router.get(
    "/candidates/{candidate_id}/attachments/{att_id}/download",
    tags=[_TAG],
)
async def download_attachment(
    candidate_id: int,
    att_id: int,
    current_user: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    from app.services.candidate_import_service import get_attachment_download
    return await get_attachment_download(session, candidate_id, att_id)


# ── Applications ──────────────────────────────────────────────────────────────


@router.post(
    "/candidates/{candidate_id}/apply",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
)
async def apply_candidate(
    candidate_id: int,
    data: ApplicationCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await candidate_service.apply_candidate(session, candidate_id, data, current_user.id)
    await auth_service.log_audit(
        session, current_user.id, "CREATE",
        entity_type="candidate_application", entity_id=result.id,
        entity_name=f"candidate#{candidate_id} → JR#{data.job_requisition_id}",
    )
    await session.commit()
    return result


@router.get(
    "/job-requisitions/{jr_id}/applications",
    response_model=ApplicationListPage,
    tags=[_TAG],
)
async def list_applications(
    jr_id: int,
    stage: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await candidate_service.list_applications(session, jr_id, stage, page, page_size)


@router.get(
    "/candidates/{candidate_id}/applications",
    response_model=ApplicationListPage,
    tags=[_TAG],
)
async def list_candidate_applications(
    candidate_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await candidate_service.list_candidate_applications(session, candidate_id, page, page_size)
