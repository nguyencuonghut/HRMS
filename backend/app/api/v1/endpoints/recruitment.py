"""Endpoints tuyển dụng ATS — 13.1 Kế hoạch & Yêu cầu tuyển dụng / 13.2 Đăng tin / 13.3 Ứng viên."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_permission
from app.core.database import get_session
from app.models.auth import User
from app.schemas.recruitment import (
    ApplicationCreate,
    ApplicationListPage,
    ApplicationRead,
    AdvanceApplicationRequest,
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
    CandidateStageResultRead,
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
    InterviewCancelRequest,
    InterviewPanelistRead,
    InterviewQuestionCreate,
    InterviewQuestionRead,
    InterviewQuestionUpdate,
    InterviewSessionCreate,
    InterviewSessionRead,
    InterviewSessionUpdate,
    JobPostingCreate,
    JobPostingListPage,
    JobPostingRead,
    JobPostingUpdate,
    JobRequisitionCreate,
    KanbanBoard,
    JobRequisitionListPage,
    JobRequisitionRead,
    JobRequisitionUpdate,
    LanguageValidationRequest,
    LanguageValidationResult,
    HoldApplicationRequest,
    PanelistScoreSubmit,
    PipelineSetupRequest,
    PipelineStageRead,
    PipelineStageTemplateCreate,
    PipelineStageTemplateRead,
    PipelineStageTemplateUpdate,
    PipelineStageUpdate,
    RecruitmentChannelCreate,
    RecruitmentChannelRead,
    RecruitmentChannelUpdate,
    RejectRequest,
    ScorecardCriterionCreate,
    ScorecardCriterionRead,
    ScorecardCriterionUpdate,
    StageResultUpsert,
    ConvertToEmployeeResult,
    HiringDecisionCreate,
    HiringDecisionRead,
    HiringDecisionUpdate,
    OfferCreate,
    OfferNegotiateRequest,
    OfferRead,
    OfferRejectRequest,
    OfferUpdate,
)
from app.services import (
    auth_service,
    candidate_service,
    headcount_plan_service,
    hiring_decision_service,
    interview_service,
    job_posting_service,
    jr_service,
    offer_service,
    pipeline_service,
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
    "/applications/{application_id}",
    response_model=ApplicationRead,
    tags=[_TAG],
)
async def get_application(
    application_id: int,
    current_user: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await candidate_service.get_application(session, application_id)


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


# ── Pipeline Templates / Stages / Kanban (13.4) ─────────────────────────────


@router.get("/pipeline-templates", response_model=List[PipelineStageTemplateRead], tags=[_TAG])
async def list_pipeline_templates(
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await pipeline_service.list_pipeline_templates(session)


@router.post(
    "/pipeline-templates",
    response_model=PipelineStageTemplateRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
)
async def create_pipeline_template(
    data: PipelineStageTemplateCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await pipeline_service.create_pipeline_template(session, data, current_user.id)
    await session.commit()
    return result


@router.put("/pipeline-templates/{template_id}", response_model=PipelineStageTemplateRead, tags=[_TAG])
async def update_pipeline_template(
    template_id: int,
    data: PipelineStageTemplateUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await pipeline_service.update_pipeline_template(session, template_id, data)
    await session.commit()
    return result


@router.delete("/pipeline-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT, tags=[_TAG])
async def delete_pipeline_template(
    template_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await pipeline_service.delete_pipeline_template(session, template_id)
    await session.commit()


@router.get("/job-requisitions/{jr_id}/pipeline", response_model=List[PipelineStageRead], tags=[_TAG])
async def list_pipeline_for_jr(
    jr_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await pipeline_service.list_pipeline_for_jr(session, jr_id)


@router.post("/job-requisitions/{jr_id}/pipeline", response_model=List[PipelineStageRead], tags=[_TAG])
async def setup_pipeline_for_jr(
    jr_id: int,
    data: PipelineSetupRequest,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await pipeline_service.setup_pipeline_for_jr(session, jr_id, data)
    await session.commit()
    return result


@router.put("/job-requisitions/{jr_id}/pipeline/{stage_id}", response_model=PipelineStageRead, tags=[_TAG])
async def update_pipeline_stage(
    jr_id: int,
    stage_id: int,
    data: PipelineStageUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await pipeline_service.update_pipeline_stage(session, jr_id, stage_id, data)
    await session.commit()
    return result


@router.delete("/job-requisitions/{jr_id}/pipeline/{stage_id}", status_code=status.HTTP_204_NO_CONTENT, tags=[_TAG])
async def delete_pipeline_stage(
    jr_id: int,
    stage_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await pipeline_service.delete_pipeline_stage(session, jr_id, stage_id)
    await session.commit()


@router.post("/applications/{application_id}/advance", response_model=ApplicationRead, tags=[_TAG])
async def advance_application(
    application_id: int,
    data: AdvanceApplicationRequest,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await pipeline_service.advance_application(session, application_id, data, current_user.id)
    await session.commit()
    return result


@router.post("/applications/{application_id}/reject", response_model=ApplicationRead, tags=[_TAG])
async def reject_application(
    application_id: int,
    data: RejectRequest,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await pipeline_service.reject_application(session, application_id, data, current_user.id)
    await session.commit()
    return result


@router.post("/applications/{application_id}/hold", response_model=ApplicationRead, tags=[_TAG])
async def hold_application(
    application_id: int,
    data: HoldApplicationRequest,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await pipeline_service.hold_application(session, application_id, data, current_user.id)
    await session.commit()
    return result


@router.get("/job-requisitions/{jr_id}/kanban", response_model=KanbanBoard, tags=[_TAG])
async def get_kanban(
    jr_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await pipeline_service.get_kanban(session, jr_id)


@router.post(
    "/applications/{application_id}/stages/{stage_id}/result",
    response_model=CandidateStageResultRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
)
async def create_stage_result(
    application_id: int,
    stage_id: int,
    data: StageResultUpsert,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await pipeline_service.upsert_stage_result(session, application_id, stage_id, data, current_user.id)
    await session.commit()
    return result


@router.put(
    "/applications/{application_id}/stages/{stage_id}/result",
    response_model=CandidateStageResultRead,
    tags=[_TAG],
)
async def update_stage_result(
    application_id: int,
    stage_id: int,
    data: StageResultUpsert,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await pipeline_service.upsert_stage_result(session, application_id, stage_id, data, current_user.id)
    await session.commit()
    return result


@router.get("/applications/{application_id}/stages", response_model=List[CandidateStageResultRead], tags=[_TAG])
async def list_stage_results(
    application_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await pipeline_service.list_stage_results(session, application_id)


# ── Interviews / Scorecard (13.4) ────────────────────────────────────────────


@router.post(
    "/applications/{application_id}/interviews",
    response_model=InterviewSessionRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_TAG],
)
async def create_interview(
    application_id: int,
    data: InterviewSessionCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await interview_service.create_interview(session, application_id, data, current_user.id)
    await session.commit()
    return result


@router.get("/applications/{application_id}/interviews", response_model=List[InterviewSessionRead], tags=[_TAG])
async def list_application_interviews(
    application_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await interview_service.list_application_interviews(session, application_id)


@router.get("/interviews/{interview_id}", response_model=InterviewSessionRead, tags=[_TAG])
async def get_interview(
    interview_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await interview_service.get_interview(session, interview_id)


@router.put("/interviews/{interview_id}", response_model=InterviewSessionRead, tags=[_TAG])
async def update_interview(
    interview_id: int,
    data: InterviewSessionUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await interview_service.update_interview(session, interview_id, data)
    await session.commit()
    return result


@router.post("/interviews/{interview_id}/complete", response_model=InterviewSessionRead, tags=[_TAG])
async def complete_interview(
    interview_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await interview_service.complete_interview(session, interview_id, current_user.id)
    await session.commit()
    return result


@router.post("/interviews/{interview_id}/cancel", response_model=InterviewSessionRead, tags=[_TAG])
async def cancel_interview(
    interview_id: int,
    data: InterviewCancelRequest,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await interview_service.cancel_interview(session, interview_id, data)
    await session.commit()
    return result


@router.post("/interviews/{interview_id}/panelists/{user_id}/score", response_model=InterviewPanelistRead, tags=[_TAG])
async def submit_panelist_score(
    interview_id: int,
    user_id: int,
    data: PanelistScoreSubmit,
    current_user: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    result = await interview_service.submit_panelist_score(session, interview_id, user_id, current_user, data)
    await session.commit()
    return result


@router.put("/interviews/{interview_id}/panelists/{user_id}/score", response_model=InterviewPanelistRead, tags=[_TAG])
async def update_panelist_score(
    interview_id: int,
    user_id: int,
    data: PanelistScoreSubmit,
    current_user: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    result = await interview_service.submit_panelist_score(session, interview_id, user_id, current_user, data)
    await session.commit()
    return result


# ── Interview Kit (13.4) ─────────────────────────────────────────────────────


@router.get("/questions", response_model=List[InterviewQuestionRead], tags=[_TAG])
async def list_questions(
    job_position_id: Optional[int] = Query(default=None),
    category: Optional[str] = Query(default=None),
    stage_type: Optional[str] = Query(default=None),
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await interview_service.list_questions(session, job_position_id, category, stage_type)


@router.post("/questions", response_model=InterviewQuestionRead, status_code=status.HTTP_201_CREATED, tags=[_TAG])
async def create_question(
    data: InterviewQuestionCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await interview_service.create_question(session, data, current_user.id)
    await session.commit()
    return result


@router.put("/questions/{question_id}", response_model=InterviewQuestionRead, tags=[_TAG])
async def update_question(
    question_id: int,
    data: InterviewQuestionUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await interview_service.update_question(session, question_id, data)
    await session.commit()
    return result


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT, tags=[_TAG])
async def delete_question(
    question_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await interview_service.delete_question(session, question_id)
    await session.commit()


@router.get("/scorecard-criteria", response_model=List[ScorecardCriterionRead], tags=[_TAG])
async def list_scorecard_criteria(
    job_position_id: Optional[int] = Query(default=None),
    stage_type: Optional[str] = Query(default=None),
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await interview_service.list_scorecard_criteria(session, job_position_id, stage_type)


@router.post("/scorecard-criteria", response_model=ScorecardCriterionRead, status_code=status.HTTP_201_CREATED, tags=[_TAG])
async def create_scorecard_criterion(
    data: ScorecardCriterionCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await interview_service.create_scorecard_criterion(session, data)
    await session.commit()
    return result


@router.put("/scorecard-criteria/{criterion_id}", response_model=ScorecardCriterionRead, tags=[_TAG])
async def update_scorecard_criterion(
    criterion_id: int,
    data: ScorecardCriterionUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await interview_service.update_scorecard_criterion(session, criterion_id, data)
    await session.commit()
    return result


@router.delete("/scorecard-criteria/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT, tags=[_TAG])
async def delete_scorecard_criterion(
    criterion_id: int,
    _: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    await interview_service.delete_scorecard_criterion(session, criterion_id)
    await session.commit()


# ── Offer ─────────────────────────────────────────────────────────────────────

_OFFER_TAG = "Offer & Quyết định tuyển dụng"


@router.get("/applications/{application_id}/offers", response_model=List[OfferRead], tags=[_OFFER_TAG])
async def list_offers(
    application_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await offer_service.list_offers_for_application(session, application_id)


@router.post(
    "/applications/{application_id}/offers",
    response_model=OfferRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_OFFER_TAG],
)
async def create_offer(
    application_id: int,
    data: OfferCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await offer_service.create_offer(session, application_id, data, current_user.id)
    await session.commit()
    return result


@router.get("/offers/{offer_id}", response_model=OfferRead, tags=[_OFFER_TAG])
async def get_offer(
    offer_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await offer_service.get_offer(session, offer_id)


@router.put("/offers/{offer_id}", response_model=OfferRead, tags=[_OFFER_TAG])
async def update_offer(
    offer_id: int,
    data: OfferUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await offer_service.update_offer(session, offer_id, data, current_user.id)
    await session.commit()
    return result


@router.post("/offers/{offer_id}/send", response_model=OfferRead, tags=[_OFFER_TAG])
async def send_offer(
    offer_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await offer_service.send_offer(session, offer_id, current_user.id)
    await session.commit()
    return result


@router.post("/offers/{offer_id}/accept", response_model=OfferRead, tags=[_OFFER_TAG])
async def accept_offer(
    offer_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await offer_service.accept_offer(session, offer_id, current_user.id)
    await session.commit()
    return result


@router.post("/offers/{offer_id}/reject", response_model=OfferRead, tags=[_OFFER_TAG])
async def reject_offer(
    offer_id: int,
    data: OfferRejectRequest,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await offer_service.reject_offer(session, offer_id, data, current_user.id)
    await session.commit()
    return result


@router.post("/offers/{offer_id}/negotiate", response_model=OfferRead, tags=[_OFFER_TAG])
async def negotiate_offer(
    offer_id: int,
    data: OfferNegotiateRequest,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await offer_service.negotiate_offer(session, offer_id, data, current_user.id)
    await session.commit()
    return result


# ── Hiring Decision ───────────────────────────────────────────────────────────


@router.post(
    "/offers/{offer_id}/hiring-decision",
    response_model=HiringDecisionRead,
    status_code=status.HTTP_201_CREATED,
    tags=[_OFFER_TAG],
)
async def create_hiring_decision(
    offer_id: int,
    data: HiringDecisionCreate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await hiring_decision_service.create_decision(session, offer_id, data, current_user.id)
    await session.commit()
    return result


@router.get("/offers/{offer_id}/hiring-decision", response_model=HiringDecisionRead, tags=[_OFFER_TAG])
async def get_hiring_decision_for_offer(
    offer_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    result = await hiring_decision_service.get_decision_for_offer(session, offer_id)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Chưa có quyết định tuyển dụng cho offer này")
    return result


@router.get("/hiring-decisions/{decision_id}", response_model=HiringDecisionRead, tags=[_OFFER_TAG])
async def get_hiring_decision(
    decision_id: int,
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await hiring_decision_service.get_decision(session, decision_id)


@router.put("/hiring-decisions/{decision_id}", response_model=HiringDecisionRead, tags=[_OFFER_TAG])
async def update_hiring_decision(
    decision_id: int,
    data: HiringDecisionUpdate,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await hiring_decision_service.update_decision(session, decision_id, data, current_user.id)
    await session.commit()
    return result


@router.post(
    "/hiring-decisions/{decision_id}/convert",
    response_model=ConvertToEmployeeResult,
    tags=[_OFFER_TAG],
)
async def convert_to_employee(
    decision_id: int,
    current_user: User = require_permission("recruitment:manage"),
    session: AsyncSession = Depends(get_session),
):
    result = await hiring_decision_service.convert_to_employee(session, decision_id, current_user.id)
    await session.commit()
    return result


# ── Document Checklist Types (admin) ──────────────────────────────────────────
from app.services import document_checklist_service as _doc_svc
from app.services.document_checklist_service import EmployeeChecklistSummary

_DOC_TAG = "Document Checklist"


@router.get("/document-types", response_model=list, tags=[_DOC_TAG])
async def list_document_types(
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    from app.models.recruitment import DocumentChecklistType
    rows = (await session.execute(
        select(DocumentChecklistType)
        .where(DocumentChecklistType.is_active == True)
        .order_by(DocumentChecklistType.sort_order)
    )).scalars().all()
    return [
        {"id": r.id, "code": r.code, "name": r.name, "is_required": r.is_required,
         "has_expiry": r.has_expiry, "applies_to": r.applies_to, "sort_order": r.sort_order}
        for r in rows
    ]


@router.get(
    "/document-checklist/summary",
    response_model=list[EmployeeChecklistSummary],
    tags=[_DOC_TAG],
)
async def missing_documents_report(
    status: Optional[str] = Query(None, description="complete | incomplete | expiring"),
    department_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, description="Tìm theo họ tên nhân viên"),
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    return await _doc_svc.get_missing_documents_report(session, status, department_id, search)


@router.get("/labor-report/export", tags=[_DOC_TAG])
async def export_labor_report(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    _: User = require_permission("recruitment:view"),
    session: AsyncSession = Depends(get_session),
):
    data = await _doc_svc.export_labor_report_excel(session, year, month)
    filename = f"lao_dong_moi_{year}_{month:02d}.xlsx"
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
