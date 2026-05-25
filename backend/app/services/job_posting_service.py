"""Service đăng tin tuyển dụng (Job Posting) — 13.2."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.org import Department, JobPosition
from app.models.recruitment import JobPosting, JobRequisition, RecruitmentChannel
from app.schemas.recruitment import (
    JobPostingCreate,
    JobPostingListPage,
    JobPostingRead,
    JobPostingUpdate,
    LanguageValidationResult,
    PostingStatusLabels,
    PostingTypeLabels,
    RecruitmentChannelCreate,
    RecruitmentChannelRead,
    RecruitmentChannelUpdate,
)

logger = logging.getLogger(__name__)

_DISCRIMINATORY_KEYWORDS = [
    "nam giới", "nữ giới", "độc thân", "chưa kết hôn", "không có con",
    "dưới 30 tuổi", "dưới 25 tuổi", "dưới 35 tuổi",
    "ưu tiên nam", "ưu tiên nữ", "chỉ nhận nam", "chỉ nhận nữ",
    "ngoại hình ưa nhìn", "chiều cao", "cân nặng",
    "không mang thai", "không có gia đình",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Channel ───────────────────────────────────────────────────────────────────


async def list_channels(session: AsyncSession) -> list[RecruitmentChannelRead]:
    result = await session.execute(
        select(RecruitmentChannel).order_by(RecruitmentChannel.sort_order, RecruitmentChannel.id)
    )
    return [RecruitmentChannelRead.model_validate(c) for c in result.scalars().all()]


async def create_channel(
    session: AsyncSession, data: RecruitmentChannelCreate
) -> RecruitmentChannelRead:
    existing = (
        await session.execute(
            select(RecruitmentChannel).where(RecruitmentChannel.code == data.code)
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Mã kênh '{data.code}' đã tồn tại")

    channel = RecruitmentChannel(**data.model_dump())
    session.add(channel)
    await session.flush()
    return RecruitmentChannelRead.model_validate(channel)


async def update_channel(
    session: AsyncSession, channel_id: int, data: RecruitmentChannelUpdate
) -> RecruitmentChannelRead:
    channel = await session.get(RecruitmentChannel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kênh tuyển dụng không tồn tại")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(channel, k, v)
    await session.flush()
    return RecruitmentChannelRead.model_validate(channel)


async def delete_channel(session: AsyncSession, channel_id: int) -> None:
    channel = await session.get(RecruitmentChannel, channel_id)
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kênh tuyển dụng không tồn tại")

    # Kiểm tra kênh có đang được dùng trong posting nào không
    count = (
        await session.execute(
            select(func.count()).where(JobPosting.channels.contains([channel_id]))
        )
    ).scalar_one()
    if count > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Kênh đang được dùng trong {count} tin tuyển dụng, không thể xóa",
        )
    await session.delete(channel)
    await session.flush()


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _validate_channels(session: AsyncSession, channel_ids: list[int]) -> None:
    if not channel_ids:
        return
    result = await session.execute(
        select(RecruitmentChannel).where(RecruitmentChannel.id.in_(channel_ids))
    )
    found = {c.id: c for c in result.scalars().all()}
    for ch_id in channel_ids:
        ch = found.get(ch_id)
        if not ch or not ch.is_active:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Kênh tuyển dụng ID={ch_id} không tồn tại hoặc đã dừng hoạt động",
            )


async def _get_channel_objects(
    session: AsyncSession, ids: list[int]
) -> list[RecruitmentChannelRead]:
    if not ids:
        return []
    result = await session.execute(
        select(RecruitmentChannel).where(RecruitmentChannel.id.in_(ids))
    )
    by_id = {c.id: c for c in result.scalars().all()}
    return [RecruitmentChannelRead.model_validate(by_id[i]) for i in ids if i in by_id]


async def _build_read(session: AsyncSession, posting: JobPosting) -> JobPostingRead:
    jr   = await session.get(JobRequisition, posting.job_requisition_id)
    pos  = await session.get(JobPosition, jr.job_position_id) if jr else None
    dept = await session.get(Department, jr.department_id) if jr else None
    creator = await session.get(User, posting.created_by_id)
    channels = await _get_channel_objects(session, posting.channels or [])

    return JobPostingRead(
        id=posting.id,
        job_requisition_id=posting.job_requisition_id,
        job_requisition_code=jr.code if jr else "—",
        job_position_name=pos.name if pos else "—",
        department_name=dept.name if dept else "—",
        title=posting.title,
        description=posting.description,
        requirements=posting.requirements,
        benefits=posting.benefits,
        work_location=posting.work_location,
        deadline=posting.deadline,
        salary_display=posting.salary_display,
        posting_type=posting.posting_type,
        posting_type_label=PostingTypeLabels.get(posting.posting_type, posting.posting_type),
        channels=channels,
        status=posting.status,
        status_label=PostingStatusLabels.get(posting.status, posting.status),
        opened_at=posting.opened_at,
        closed_at=posting.closed_at,
        candidate_count=0,  # placeholder — populated in 13.3
        note=posting.note,
        created_by_name=creator.full_name if creator else None,
        created_at=posting.created_at,
        updated_at=posting.updated_at,
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def list_postings(
    session: AsyncSession,
    status: Optional[str] = None,
    job_requisition_id: Optional[int] = None,
    posting_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> JobPostingListPage:
    q = select(JobPosting)
    if status:
        q = q.where(JobPosting.status == status)
    if job_requisition_id:
        q = q.where(JobPosting.job_requisition_id == job_requisition_id)
    if posting_type:
        q = q.where(JobPosting.posting_type == posting_type)

    total = (
        await session.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    rows = (
        await session.execute(
            q.order_by(JobPosting.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    items = [await _build_read(session, p) for p in rows]
    return JobPostingListPage(items=items, total=total, page=page, page_size=page_size)


async def get_posting(session: AsyncSession, posting_id: int) -> JobPostingRead:
    posting = await session.get(JobPosting, posting_id)
    if not posting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tin tuyển dụng không tồn tại")
    return await _build_read(session, posting)


async def create_posting(
    session: AsyncSession, data: JobPostingCreate, created_by_id: int
) -> JobPostingRead:
    # Validate JR
    jr = await session.get(JobRequisition, data.job_requisition_id)
    if not jr:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Yêu cầu tuyển dụng không tồn tại")
    if jr.status not in ("approved", "in_progress"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Yêu cầu tuyển dụng phải ở trạng thái Đã duyệt hoặc Đang tuyển",
        )

    await _validate_channels(session, data.channels)

    if data.deadline and data.deadline < date.today():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Hạn nộp hồ sơ không được trong quá khứ"
        )

    now = _utcnow()
    posting = JobPosting(
        job_requisition_id=data.job_requisition_id,
        title=data.title,
        description=data.description,
        requirements=data.requirements,
        benefits=data.benefits,
        work_location=data.work_location,
        deadline=data.deadline,
        salary_display=data.salary_display,
        posting_type=data.posting_type,
        channels=data.channels or [],
        status="draft",
        note=data.note,
        created_by_id=created_by_id,
        created_at=now,
        updated_at=now,
    )
    session.add(posting)
    await session.flush()
    return await _build_read(session, posting)


async def update_posting(
    session: AsyncSession, posting_id: int, data: JobPostingUpdate
) -> JobPostingRead:
    posting = await session.get(JobPosting, posting_id)
    if not posting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tin tuyển dụng không tồn tại")
    if posting.status not in ("draft", "active"):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Chỉ có thể sửa tin ở trạng thái Nháp hoặc Đang tuyển"
        )

    updates = data.model_dump(exclude_none=True)
    if "channels" in updates:
        await _validate_channels(session, updates["channels"])
    if "deadline" in updates and updates["deadline"] and updates["deadline"] < date.today():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Hạn nộp hồ sơ không được trong quá khứ"
        )

    for k, v in updates.items():
        setattr(posting, k, v)
    posting.updated_at = _utcnow()
    await session.flush()
    return await _build_read(session, posting)


# ── Workflow ──────────────────────────────────────────────────────────────────


async def publish_posting(session: AsyncSession, posting_id: int) -> JobPostingRead:
    posting = await session.get(JobPosting, posting_id)
    if not posting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tin tuyển dụng không tồn tại")
    if posting.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "Chỉ có thể đăng tin ở trạng thái Nháp")

    now = _utcnow()
    posting.status = "active"
    posting.opened_at = now
    posting.updated_at = now

    # Cập nhật JR → in_progress nếu đang ở approved
    jr = await session.get(JobRequisition, posting.job_requisition_id)
    if jr and jr.status == "approved":
        jr.status = "in_progress"
        jr.updated_at = now

    await session.flush()
    return await _build_read(session, posting)


async def close_posting(session: AsyncSession, posting_id: int) -> JobPostingRead:
    posting = await session.get(JobPosting, posting_id)
    if not posting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tin tuyển dụng không tồn tại")
    if posting.status != "active":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Chỉ có thể đóng tin đang ở trạng thái Đang tuyển"
        )

    now = _utcnow()
    posting.status = "closed"
    posting.closed_at = now
    posting.updated_at = now
    await session.flush()
    return await _build_read(session, posting)


async def reopen_posting(session: AsyncSession, posting_id: int) -> JobPostingRead:
    posting = await session.get(JobPosting, posting_id)
    if not posting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tin tuyển dụng không tồn tại")
    if posting.status != "closed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Chỉ có thể mở lại tin đã đóng")
    if posting.deadline and posting.deadline < date.today():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Không thể mở lại: hạn nộp hồ sơ đã qua",
        )

    now = _utcnow()
    posting.status = "active"
    posting.closed_at = None
    posting.updated_at = now
    await session.flush()
    return await _build_read(session, posting)


# ── Language validation ───────────────────────────────────────────────────────


def validate_language(text: str) -> LanguageValidationResult:
    text_lower = text.lower()
    warnings = [kw for kw in _DISCRIMINATORY_KEYWORDS if kw in text_lower]
    return LanguageValidationResult(warnings=warnings)


# ── Scheduled task helper ─────────────────────────────────────────────────────


async def expire_stale_postings(session: AsyncSession) -> int:
    result = await session.execute(
        update(JobPosting)
        .where(
            JobPosting.status == "active",
            JobPosting.deadline.isnot(None),
            JobPosting.deadline < date.today(),
        )
        .values(status="expired", updated_at=_utcnow())
        .execution_options(synchronize_session=False)
    )
    await session.commit()
    return result.rowcount
