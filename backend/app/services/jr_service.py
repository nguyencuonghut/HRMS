"""Service Yêu cầu tuyển dụng (Job Requisition) — 13.1."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.org import Department, JobPosition
from app.models.recruitment import HeadcountPlan, JobRequisition, RecruitmentBudgetItem
from app.schemas.recruitment import (
    JRReasonLabels,
    JRStatusLabels,
    BudgetItemCreate,
    BudgetItemRead,
    BudgetItemUpdate,
    BudgetSummary,
    CancelRequest,
    JobRequisitionCreate,
    JobRequisitionListItem,
    JobRequisitionListPage,
    JobRequisitionRead,
    JobRequisitionUpdate,
    RejectRequest,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_jr_or_404(session: AsyncSession, jr_id: int) -> JobRequisition:
    jr = await session.get(JobRequisition, jr_id)
    if not jr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy yêu cầu tuyển dụng")
    return jr


async def _build_read(session: AsyncSession, jr: JobRequisition) -> JobRequisitionRead:
    pos = await session.get(JobPosition, jr.job_position_id)
    dept = await session.get(Department, jr.department_id)
    creator = await session.get(User, jr.created_by_id) if jr.created_by_id else None
    submitter = await session.get(User, jr.submitted_by_id) if jr.submitted_by_id else None
    approver = await session.get(User, jr.approved_by_id) if jr.approved_by_id else None

    effective_description = jr.jd_description or (pos.description if pos else None)
    effective_requirements = jr.jd_requirements or (pos.requirements if pos else None)

    return JobRequisitionRead(
        id=jr.id,
        code=jr.code,
        job_position_id=jr.job_position_id,
        job_position_name=pos.name if pos else "",
        department_id=jr.department_id,
        department_name=dept.name if dept else "",
        headcount_plan_id=jr.headcount_plan_id,
        quantity=jr.quantity,
        quantity_remaining=jr.quantity_remaining,
        reason_type=jr.reason_type,
        reason_type_label=JRReasonLabels.get(jr.reason_type, jr.reason_type),
        deadline=jr.deadline,
        salary_min=jr.salary_min,
        salary_max=jr.salary_max,
        effective_description=effective_description,
        effective_requirements=effective_requirements,
        status=jr.status,
        status_label=JRStatusLabels.get(jr.status, jr.status),
        submitted_at=jr.submitted_at,
        submitted_by_name=submitter.full_name if submitter else None,
        approved_by_id=jr.approved_by_id,
        approved_by_name=approver.full_name if approver else None,
        approved_at=jr.approved_at,
        rejection_note=jr.rejection_note,
        internal_note=jr.internal_note,
        created_by_id=jr.created_by_id,
        created_by_name=creator.full_name if creator else None,
        created_at=jr.created_at,
        updated_at=jr.updated_at,
    )


async def _build_list_item(session: AsyncSession, jr: JobRequisition) -> JobRequisitionListItem:
    pos = await session.get(JobPosition, jr.job_position_id)
    dept = await session.get(Department, jr.department_id)
    return JobRequisitionListItem(
        id=jr.id,
        code=jr.code,
        job_position_name=pos.name if pos else "",
        department_name=dept.name if dept else "",
        quantity=jr.quantity,
        quantity_remaining=jr.quantity_remaining,
        reason_type=jr.reason_type,
        reason_type_label=JRReasonLabels.get(jr.reason_type, jr.reason_type),
        deadline=jr.deadline,
        status=jr.status,
        status_label=JRStatusLabels.get(jr.status, jr.status),
        created_at=jr.created_at,
    )


async def _generate_jr_code(session: AsyncSession, year: int) -> str:
    """Sinh mã JR theo format JR-{year}-{seq:04d}, sequence reset mỗi năm."""
    prefix_like = f"JR-{year}-%"
    stmt = select(func.count()).where(JobRequisition.code.like(prefix_like))
    count = (await session.execute(stmt)).scalar_one()
    seq = count + 1
    # Dùng vòng lặp phòng trường hợp trùng (race condition thấp — sequence tự tăng)
    while True:
        code = f"JR-{year}-{seq:04d}"
        existing = (
            await session.execute(select(JobRequisition).where(JobRequisition.code == code))
        ).scalar_one_or_none()
        if not existing:
            return code
        seq += 1


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def list_job_requisitions(
    session: AsyncSession,
    *,
    status: Optional[str] = None,
    department_id: Optional[int] = None,
    job_position_id: Optional[int] = None,
    year: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> JobRequisitionListPage:
    stmt = select(JobRequisition)

    if status is not None:
        stmt = stmt.where(JobRequisition.status == status)
    if department_id is not None:
        stmt = stmt.where(JobRequisition.department_id == department_id)
    if job_position_id is not None:
        stmt = stmt.where(JobRequisition.job_position_id == job_position_id)
    if year is not None:
        stmt = stmt.where(JobRequisition.code.like(f"JR-{year}-%"))
    if search:
        kw = f"%{search.strip()}%"
        stmt = stmt.join(JobPosition, JobPosition.id == JobRequisition.job_position_id).where(
            or_(
                JobRequisition.code.ilike(kw),
                JobPosition.name.ilike(kw),
            )
        )

    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(total_stmt)).scalar_one()

    stmt = stmt.order_by(JobRequisition.created_at.desc(), JobRequisition.id.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    records = (await session.execute(stmt)).scalars().all()

    items = [await _build_list_item(session, r) for r in records]
    return JobRequisitionListPage(items=items, total=total, page=page, page_size=page_size)


async def get_job_requisition(session: AsyncSession, jr_id: int) -> JobRequisitionRead:
    jr = await _get_jr_or_404(session, jr_id)
    return await _build_read(session, jr)


async def create_job_requisition(
    session: AsyncSession,
    data: JobRequisitionCreate,
    created_by_id: int,
) -> JobRequisitionRead:
    pos = await session.get(JobPosition, data.job_position_id)
    if not pos:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy vị trí công việc")

    dept = await session.get(Department, data.department_id)
    if not dept:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng ban")

    if data.headcount_plan_id is not None:
        plan = await session.get(HeadcountPlan, data.headcount_plan_id)
        if not plan:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kế hoạch nhân sự")
        if plan.department_id is not None and plan.department_id != data.department_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Kế hoạch nhân sự không thuộc phòng ban được chọn",
            )

    year = _utcnow().year
    code = await _generate_jr_code(session, year)

    jr = JobRequisition(
        code=code,
        job_position_id=data.job_position_id,
        department_id=data.department_id,
        headcount_plan_id=data.headcount_plan_id,
        quantity=data.quantity,
        quantity_remaining=data.quantity,
        reason_type=data.reason_type,
        deadline=data.deadline,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        jd_description=data.jd_description,
        jd_requirements=data.jd_requirements,
        internal_note=data.internal_note,
        status="draft",
        created_by_id=created_by_id,
    )
    session.add(jr)
    await session.flush()
    return await _build_read(session, jr)


async def update_job_requisition(
    session: AsyncSession,
    jr_id: int,
    data: JobRequisitionUpdate,
) -> JobRequisitionRead:
    jr = await _get_jr_or_404(session, jr_id)

    if jr.status not in ("draft", "pending_review"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Không thể sửa JR ở trạng thái '{jr.status}'",
        )

    if data.department_id is not None:
        dept = await session.get(Department, data.department_id)
        if not dept:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy phòng ban")
        jr.department_id = data.department_id

    if data.headcount_plan_id is not None:
        plan = await session.get(HeadcountPlan, data.headcount_plan_id)
        if not plan:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kế hoạch nhân sự")
        jr.headcount_plan_id = data.headcount_plan_id

    for field in ("quantity", "reason_type", "deadline", "salary_min", "salary_max",
                  "jd_description", "jd_requirements", "internal_note"):
        val = getattr(data, field)
        if val is not None:
            setattr(jr, field, val)

    if data.quantity is not None and jr.status == "draft":
        jr.quantity_remaining = data.quantity

    jr.updated_at = _utcnow()
    session.add(jr)
    await session.flush()
    return await _build_read(session, jr)


async def delete_job_requisition(session: AsyncSession, jr_id: int) -> None:
    jr = await _get_jr_or_404(session, jr_id)
    if jr.status != "draft":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể xóa JR ở trạng thái 'Nháp'",
        )
    await session.delete(jr)


# ── Workflow ──────────────────────────────────────────────────────────────────


async def submit_job_requisition(
    session: AsyncSession,
    jr_id: int,
    user_id: int,
) -> JobRequisitionRead:
    jr = await _get_jr_or_404(session, jr_id)
    if jr.status != "draft":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể gửi duyệt JR ở trạng thái 'Nháp'",
        )
    jr.status = "pending_review"
    jr.submitted_by_id = user_id
    jr.submitted_at = _utcnow()
    jr.rejection_note = None
    jr.updated_at = _utcnow()
    session.add(jr)
    await session.flush()
    return await _build_read(session, jr)


async def approve_job_requisition(
    session: AsyncSession,
    jr_id: int,
    user_id: int,
) -> JobRequisitionRead:
    jr = await _get_jr_or_404(session, jr_id)
    if jr.status != "pending_review":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể duyệt JR ở trạng thái 'Chờ duyệt'",
        )
    jr.status = "approved"
    jr.approved_by_id = user_id
    jr.approved_at = _utcnow()
    jr.updated_at = _utcnow()
    session.add(jr)
    await session.flush()
    return await _build_read(session, jr)


async def reject_job_requisition(
    session: AsyncSession,
    jr_id: int,
    user_id: int,
    data: RejectRequest,
) -> JobRequisitionRead:
    jr = await _get_jr_or_404(session, jr_id)
    if jr.status != "pending_review":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể từ chối JR ở trạng thái 'Chờ duyệt'",
        )
    jr.status = "draft"
    jr.rejection_note = data.rejection_note
    jr.approved_by_id = user_id
    jr.updated_at = _utcnow()
    session.add(jr)
    await session.flush()
    return await _build_read(session, jr)


async def cancel_job_requisition(
    session: AsyncSession,
    jr_id: int,
    user_id: int,
    data: CancelRequest,
) -> JobRequisitionRead:
    jr = await _get_jr_or_404(session, jr_id)
    cancellable = {"draft", "pending_review", "approved", "in_progress"}
    if jr.status not in cancellable:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Không thể hủy JR ở trạng thái '{jr.status}'",
        )
    jr.status = "cancelled"
    if data.reason:
        jr.internal_note = (jr.internal_note or "") + f"\n[Hủy] {data.reason}"
    jr.updated_at = _utcnow()
    session.add(jr)
    await session.flush()
    return await _build_read(session, jr)


# ── Budget ────────────────────────────────────────────────────────────────────


async def get_budget_summary(session: AsyncSession, jr_id: int) -> BudgetSummary:
    await _get_jr_or_404(session, jr_id)
    stmt = (
        select(RecruitmentBudgetItem)
        .where(RecruitmentBudgetItem.job_requisition_id == jr_id)
        .order_by(RecruitmentBudgetItem.id)
    )
    items = (await session.execute(stmt)).scalars().all()
    reads = [
        BudgetItemRead(
            id=it.id,
            job_requisition_id=it.job_requisition_id,
            item_name=it.item_name,
            estimated_amount=it.estimated_amount,
            actual_amount=it.actual_amount,
            note=it.note,
            created_by_id=it.created_by_id,
            created_at=it.created_at,
        )
        for it in items
    ]
    from decimal import Decimal as D
    total_estimated = sum((r.estimated_amount or D(0)) for r in reads)
    total_actual = sum((r.actual_amount or D(0)) for r in reads)
    return BudgetSummary(
        items=reads,
        total_estimated=total_estimated,
        total_actual=total_actual,
    )


async def add_budget_item(
    session: AsyncSession,
    jr_id: int,
    data: BudgetItemCreate,
    created_by_id: int,
) -> BudgetItemRead:
    await _get_jr_or_404(session, jr_id)
    item = RecruitmentBudgetItem(
        job_requisition_id=jr_id,
        item_name=data.item_name,
        estimated_amount=data.estimated_amount,
        actual_amount=data.actual_amount,
        note=data.note,
        created_by_id=created_by_id,
    )
    session.add(item)
    await session.flush()
    return BudgetItemRead(
        id=item.id,
        job_requisition_id=item.job_requisition_id,
        item_name=item.item_name,
        estimated_amount=item.estimated_amount,
        actual_amount=item.actual_amount,
        note=item.note,
        created_by_id=item.created_by_id,
        created_at=item.created_at,
    )


async def update_budget_item(
    session: AsyncSession,
    jr_id: int,
    item_id: int,
    data: BudgetItemUpdate,
) -> BudgetItemRead:
    item = await session.get(RecruitmentBudgetItem, item_id)
    if not item or item.job_requisition_id != jr_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khoản chi phí")

    for field in ("item_name", "estimated_amount", "actual_amount", "note"):
        val = getattr(data, field)
        if val is not None:
            setattr(item, field, val)

    session.add(item)
    await session.flush()
    return BudgetItemRead(
        id=item.id,
        job_requisition_id=item.job_requisition_id,
        item_name=item.item_name,
        estimated_amount=item.estimated_amount,
        actual_amount=item.actual_amount,
        note=item.note,
        created_by_id=item.created_by_id,
        created_at=item.created_at,
    )


async def delete_budget_item(session: AsyncSession, jr_id: int, item_id: int) -> None:
    item = await session.get(RecruitmentBudgetItem, item_id)
    if not item or item.job_requisition_id != jr_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy khoản chi phí")
    await session.delete(item)
