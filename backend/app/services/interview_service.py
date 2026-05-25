"""Service phỏng vấn và scorecard (13.4)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.recruitment import (
    CandidateApplication,
    InterviewPanelist,
    InterviewQuestion,
    InterviewSession,
    PipelineStage,
    ScorecardCriterion,
)
from app.schemas.recruitment import (
    InterviewCancelRequest,
    InterviewQuestionCreate,
    InterviewQuestionRead,
    InterviewQuestionUpdate,
    InterviewSessionCreate,
    InterviewSessionRead,
    InterviewSessionUpdate,
    InterviewPanelistRead,
    PanelistScoreSubmit,
    ScorecardCriterionCreate,
    ScorecardCriterionRead,
    ScorecardCriterionUpdate,
    StageResultUpsert,
)
from app.services import pipeline_service


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


async def _get_interview_or_404(session: AsyncSession, interview_id: int) -> InterviewSession:
    interview = await session.get(InterviewSession, interview_id)
    if not interview:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy lịch phỏng vấn")
    return interview


async def _panelist_read(session: AsyncSession, panelist: InterviewPanelist) -> InterviewPanelistRead:
    user = await session.get(User, panelist.user_id)
    return InterviewPanelistRead(
        id=panelist.id,
        user_id=panelist.user_id,
        user_name=user.full_name if user else None,
        criteria_scores=panelist.criteria_scores,
        overall_score=panelist.overall_score,
        result=panelist.result,
        private_notes=panelist.private_notes,
        submitted_at=panelist.submitted_at,
    )


async def _interview_read(session: AsyncSession, interview: InterviewSession) -> InterviewSessionRead:
    stage = await session.get(PipelineStage, interview.stage_id)
    creator_name = None
    if interview.created_by_id:
        creator = await session.get(User, interview.created_by_id)
        creator_name = creator.full_name if creator else None
    panelists_q = await session.execute(
        select(InterviewPanelist)
        .where(InterviewPanelist.interview_session_id == interview.id)
        .order_by(InterviewPanelist.id)
    )
    panelists = panelists_q.scalars().all()
    return InterviewSessionRead(
        id=interview.id,
        application_id=interview.application_id,
        stage_id=interview.stage_id,
        stage_name=stage.stage_name if stage else "",
        stage_type=stage.stage_type if stage else "",
        scheduled_at=interview.scheduled_at,
        duration_minutes=interview.duration_minutes,
        format=interview.format,
        location=interview.location,
        note=interview.note,
        status=interview.status,
        completed_at=interview.completed_at,
        cancel_reason=interview.cancel_reason,
        created_by_id=interview.created_by_id,
        created_by_name=creator_name,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
        panelists=[await _panelist_read(session, panelist) for panelist in panelists],
    )


async def create_interview(
    session: AsyncSession,
    application_id: int,
    data: InterviewSessionCreate,
    created_by_id: int,
) -> InterviewSessionRead:
    app = await session.get(CandidateApplication, application_id)
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ ứng tuyển")
    stage = await session.get(PipelineStage, data.stage_id)
    if not stage or stage.job_requisition_id != app.job_requisition_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="stage_id không thuộc JR của application")
    if stage.stage_type != "interview":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Chỉ được tạo lịch cho bước interview")
    scheduled_at = _normalize_utc_naive(data.scheduled_at)
    if scheduled_at <= _utcnow():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Lịch phỏng vấn phải ở tương lai")

    interview = InterviewSession(
        application_id=application_id,
        stage_id=data.stage_id,
        scheduled_at=scheduled_at,
        duration_minutes=data.duration_minutes,
        format=data.format,
        location=data.location,
        note=data.note,
        created_by_id=created_by_id,
    )
    session.add(interview)
    await session.flush()

    for panelist_user_id in sorted(set(data.panelist_user_ids)):
        user = await session.get(User, panelist_user_id)
        if not user:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy user #{panelist_user_id}")
        session.add(InterviewPanelist(interview_session_id=interview.id, user_id=panelist_user_id))
    await session.flush()
    return await _interview_read(session, interview)


async def list_application_interviews(session: AsyncSession, application_id: int) -> list[InterviewSessionRead]:
    app = await session.get(CandidateApplication, application_id)
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ ứng tuyển")
    rows_q = await session.execute(
        select(InterviewSession)
        .where(InterviewSession.application_id == application_id)
        .order_by(InterviewSession.scheduled_at.desc(), InterviewSession.id.desc())
    )
    rows = rows_q.scalars().all()
    return [await _interview_read(session, row) for row in rows]


async def get_interview(session: AsyncSession, interview_id: int) -> InterviewSessionRead:
    interview = await _get_interview_or_404(session, interview_id)
    return await _interview_read(session, interview)


async def update_interview(
    session: AsyncSession,
    interview_id: int,
    data: InterviewSessionUpdate,
) -> InterviewSessionRead:
    interview = await _get_interview_or_404(session, interview_id)
    patch = data.model_dump(exclude_unset=True)
    panelist_user_ids = patch.pop("panelist_user_ids", None)
    if "scheduled_at" in patch and patch["scheduled_at"] is not None:
        patch["scheduled_at"] = _normalize_utc_naive(patch["scheduled_at"])
        if patch["scheduled_at"] <= _utcnow():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Lịch phỏng vấn phải ở tương lai")
    for key, value in patch.items():
        setattr(interview, key, value)
    interview.updated_at = _utcnow()

    if panelist_user_ids is not None:
        existing_q = await session.execute(
            select(InterviewPanelist).where(InterviewPanelist.interview_session_id == interview.id)
        )
        existing = existing_q.scalars().all()
        existing_map = {item.user_id: item for item in existing}
        desired_ids = set(panelist_user_ids)
        for user_id, panelist in existing_map.items():
            if user_id not in desired_ids:
                await session.delete(panelist)
        for user_id in desired_ids:
            if user_id in existing_map:
                continue
            user = await session.get(User, user_id)
            if not user:
                raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Không tìm thấy user #{user_id}")
            session.add(InterviewPanelist(interview_session_id=interview.id, user_id=user_id))

    await session.flush()
    return await _interview_read(session, interview)


def _derive_overall_score(criteria_scores: list[dict]) -> Optional[Decimal]:
    if not criteria_scores:
        return None
    total = Decimal("0")
    count = 0
    for item in criteria_scores:
        try:
            score = Decimal(str(item["score"]))
            total += score
            count += 1
        except Exception:
            continue
    if count == 0:
        return None
    return (total / Decimal(count)).quantize(Decimal("0.01"))


async def submit_panelist_score(
    session: AsyncSession,
    interview_id: int,
    panelist_user_id: int,
    current_user: User,
    data: PanelistScoreSubmit,
) -> InterviewPanelistRead:
    interview = await _get_interview_or_404(session, interview_id)
    if interview.status == "cancelled":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Lịch phỏng vấn đã bị hủy")

    panelist_q = await session.execute(
        select(InterviewPanelist).where(
            InterviewPanelist.interview_session_id == interview_id,
            InterviewPanelist.user_id == panelist_user_id,
        )
    )
    panelist = panelist_q.scalars().first()
    if not panelist:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User không thuộc hội đồng phỏng vấn")
    if current_user.id != panelist_user_id and not current_user.is_superuser:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Không được phép gửi score thay cho panelist khác")

    criteria_scores = [item.model_dump(mode="json") for item in data.criteria_scores]
    panelist.criteria_scores = criteria_scores
    panelist.overall_score = data.overall_score if data.overall_score is not None else _derive_overall_score(criteria_scores)
    panelist.result = data.result
    panelist.private_notes = data.private_notes
    panelist.submitted_at = _utcnow()
    await session.flush()
    return await _panelist_read(session, panelist)


async def complete_interview(
    session: AsyncSession,
    interview_id: int,
    user_id: int,
) -> InterviewSessionRead:
    interview = await _get_interview_or_404(session, interview_id)
    if interview.status == "cancelled":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Lịch phỏng vấn đã bị hủy")

    interview.status = "completed"
    interview.completed_at = _utcnow()
    interview.updated_at = _utcnow()

    panelists_q = await session.execute(
        select(InterviewPanelist).where(InterviewPanelist.interview_session_id == interview_id)
    )
    panelists = panelists_q.scalars().all()
    submitted = [panelist for panelist in panelists if panelist.submitted_at]

    pass_count = sum(1 for panelist in submitted if panelist.result == "pass")
    fail_count = sum(1 for panelist in submitted if panelist.result == "fail")
    hold_count = sum(1 for panelist in submitted if panelist.result == "hold")
    if not submitted:
        aggregated_result = "hold"
    elif pass_count * 2 >= len(submitted):
        aggregated_result = "pass"
    elif fail_count >= hold_count:
        aggregated_result = "fail"
    else:
        aggregated_result = "hold"

    scores = [panelist.overall_score for panelist in submitted if panelist.overall_score is not None]
    aggregated_score: Optional[Decimal] = None
    if scores:
        aggregated_score = (sum(scores, Decimal("0")) / Decimal(len(scores))).quantize(Decimal("0.01"))

    await pipeline_service.upsert_stage_result(
        session,
        interview.application_id,
        interview.stage_id,
        StageResultUpsert(
            result=aggregated_result,
            score=aggregated_score,
            notes=f"Tổng hợp từ {len(submitted)}/{len(panelists)} panelist",
        ),
        user_id,
    )
    await session.flush()
    return await _interview_read(session, interview)


async def cancel_interview(
    session: AsyncSession,
    interview_id: int,
    data: InterviewCancelRequest,
) -> InterviewSessionRead:
    interview = await _get_interview_or_404(session, interview_id)
    interview.status = "cancelled"
    interview.cancel_reason = data.cancel_reason
    interview.updated_at = _utcnow()
    await session.flush()
    return await _interview_read(session, interview)


async def list_questions(
    session: AsyncSession,
    job_position_id: Optional[int],
    category: Optional[str],
    stage_type: Optional[str],
) -> list[InterviewQuestionRead]:
    query = select(InterviewQuestion).where(InterviewQuestion.is_active == True)  # noqa: E712
    if job_position_id:
        query = query.where(InterviewQuestion.job_position_id == job_position_id)
    if category:
        query = query.where(InterviewQuestion.category == category)
    if stage_type:
        query = query.where(InterviewQuestion.stage_type == stage_type)
    rows_q = await session.execute(query.order_by(InterviewQuestion.id.desc()))
    rows = rows_q.scalars().all()
    return [
        InterviewQuestionRead(
            id=row.id,
            question_text=row.question_text,
            category=row.category,
            difficulty=row.difficulty,
            job_position_id=row.job_position_id,
            stage_type=row.stage_type,
            is_active=row.is_active,
            created_by_id=row.created_by_id,
            created_at=row.created_at,
        )
        for row in rows
    ]


async def create_question(
    session: AsyncSession,
    data: InterviewQuestionCreate,
    created_by_id: int,
) -> InterviewQuestionRead:
    question = InterviewQuestion(**data.model_dump(), created_by_id=created_by_id)
    session.add(question)
    await session.flush()
    return InterviewQuestionRead.model_validate(question)


async def update_question(
    session: AsyncSession,
    question_id: int,
    data: InterviewQuestionUpdate,
) -> InterviewQuestionRead:
    question = await session.get(InterviewQuestion, question_id)
    if not question:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy câu hỏi phỏng vấn")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(question, key, value)
    await session.flush()
    return InterviewQuestionRead.model_validate(question)


async def delete_question(session: AsyncSession, question_id: int) -> None:
    question = await session.get(InterviewQuestion, question_id)
    if not question:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy câu hỏi phỏng vấn")
    await session.delete(question)
    await session.flush()


async def list_scorecard_criteria(
    session: AsyncSession,
    job_position_id: Optional[int],
    stage_type: Optional[str],
) -> list[ScorecardCriterionRead]:
    query = select(ScorecardCriterion).where(ScorecardCriterion.is_active == True)  # noqa: E712
    if job_position_id:
        query = query.where(ScorecardCriterion.job_position_id == job_position_id)
    if stage_type:
        query = query.where(ScorecardCriterion.stage_type == stage_type)
    rows_q = await session.execute(
        query.order_by(ScorecardCriterion.sort_order, ScorecardCriterion.id)
    )
    rows = rows_q.scalars().all()
    return [ScorecardCriterionRead.model_validate(row) for row in rows]


async def create_scorecard_criterion(
    session: AsyncSession,
    data: ScorecardCriterionCreate,
) -> ScorecardCriterionRead:
    criterion = ScorecardCriterion(**data.model_dump())
    session.add(criterion)
    await session.flush()
    return ScorecardCriterionRead.model_validate(criterion)


async def update_scorecard_criterion(
    session: AsyncSession,
    criterion_id: int,
    data: ScorecardCriterionUpdate,
) -> ScorecardCriterionRead:
    criterion = await session.get(ScorecardCriterion, criterion_id)
    if not criterion:
        raise HTTPException(status_code=404, detail="Không tìm thấy tiêu chí")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(criterion, field, value)
    await session.flush()
    return ScorecardCriterionRead.model_validate(criterion)


async def delete_scorecard_criterion(
    session: AsyncSession,
    criterion_id: int,
) -> None:
    criterion = await session.get(ScorecardCriterion, criterion_id)
    if not criterion:
        raise HTTPException(status_code=404, detail="Không tìm thấy tiêu chí")
    await session.delete(criterion)
    await session.flush()
