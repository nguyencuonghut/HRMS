"""Service quy trình tuyển chọn (13.4)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User
from app.models.org import Department, JobPosition
from app.models.recruitment import (
    Candidate,
    CandidateApplication,
    CandidateStageResult,
    InterviewSession,
    JobRequisition,
    PipelineStage,
    PipelineStageTemplate,
    PipelineStageTemplateItem,
    RecruitmentChannel,
)
from app.schemas.recruitment import (
    AdvanceApplicationRequest,
    ApplicationRead,
    CandidateStageResultRead,
    HoldApplicationRequest,
    KanbanBoard,
    KanbanCard,
    KanbanStage,
    PipelineSetupRequest,
    PipelineStageCreate,
    PipelineStageRead,
    PipelineStageTemplateCreate,
    PipelineStageTemplateItemInput,
    PipelineStageTemplateItemRead,
    PipelineStageTemplateRead,
    PipelineStageTemplateUpdate,
    PipelineStageUpdate,
    StageResultUpsert,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _validate_stage_definitions(stages: Iterable[PipelineStageCreate | PipelineStageTemplateItemInput]) -> None:
    stage_list = list(stages)
    if not stage_list:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Pipeline phải có ít nhất 1 bước")

    orders = [stage.stage_order for stage in stage_list]
    if len(set(orders)) != len(orders):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="stage_order không được trùng")

    types = [stage.stage_type for stage in stage_list]
    if len(set(types)) != len(types):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Mỗi JR chỉ được có tối đa 1 bước cho mỗi stage_type",
        )


async def _get_jr_or_404(session: AsyncSession, jr_id: int) -> JobRequisition:
    jr = await session.get(JobRequisition, jr_id)
    if not jr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy JR")
    return jr


async def _get_application_or_404(session: AsyncSession, application_id: int) -> CandidateApplication:
    app = await session.get(CandidateApplication, application_id)
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ ứng tuyển")
    return app


async def _get_stage_or_404(session: AsyncSession, stage_id: int) -> PipelineStage:
    stage = await session.get(PipelineStage, stage_id)
    if not stage:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bước pipeline")
    return stage


async def _get_template_or_404(session: AsyncSession, template_id: int) -> PipelineStageTemplate:
    template = await session.get(PipelineStageTemplate, template_id)
    if not template:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy mẫu pipeline")
    return template


async def _stage_read(session: AsyncSession, stage: PipelineStage) -> PipelineStageRead:
    count_q = await session.execute(
        select(func.count()).where(
            CandidateApplication.job_requisition_id == stage.job_requisition_id,
            CandidateApplication.current_stage == stage.stage_type,
        )
    )
    return PipelineStageRead(
        id=stage.id,
        job_requisition_id=stage.job_requisition_id,
        stage_order=stage.stage_order,
        stage_name=stage.stage_name,
        stage_type=stage.stage_type,
        is_active=stage.is_active,
        application_count=count_q.scalar_one(),
    )


async def _template_read(session: AsyncSession, template: PipelineStageTemplate) -> PipelineStageTemplateRead:
    items_q = await session.execute(
        select(PipelineStageTemplateItem)
        .where(PipelineStageTemplateItem.template_id == template.id)
        .order_by(PipelineStageTemplateItem.stage_order, PipelineStageTemplateItem.id)
    )
    items = items_q.scalars().all()
    return PipelineStageTemplateRead(
        id=template.id,
        name=template.name,
        job_position_id=template.job_position_id,
        is_default=template.is_default,
        created_at=template.created_at,
        items=[
            PipelineStageTemplateItemRead(
                id=item.id,
                template_id=item.template_id,
                stage_order=item.stage_order,
                stage_name=item.stage_name,
                stage_type=item.stage_type,
                is_required=item.is_required,
            )
            for item in items
        ],
    )


async def _application_read(session: AsyncSession, app: CandidateApplication) -> ApplicationRead:
    candidate = await session.get(Candidate, app.candidate_id)
    jr = await session.get(JobRequisition, app.job_requisition_id)

    pos_name = dept_name = jr_code = ""
    if jr:
        jr_code = jr.code
        pos = await session.get(JobPosition, jr.job_position_id)
        pos_name = pos.name if pos else ""
        dept = await session.get(Department, jr.department_id)
        dept_name = dept.name if dept else ""

    channel_name = None
    if app.source_channel_id:
        ch = await session.get(RecruitmentChannel, app.source_channel_id)
        channel_name = ch.name if ch else None

    return ApplicationRead(
        id=app.id,
        candidate_id=app.candidate_id,
        candidate_name=candidate.full_name if candidate else "",
        job_requisition_id=app.job_requisition_id,
        job_requisition_code=jr_code,
        job_position_name=pos_name,
        department_name=dept_name,
        applied_date=app.applied_date,
        source_channel_name=channel_name,
        current_stage=app.current_stage,
        rejection_reason=app.rejection_reason,
        internal_note=app.internal_note,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


async def _result_read(session: AsyncSession, stage_result: CandidateStageResult) -> CandidateStageResultRead:
    stage = await session.get(PipelineStage, stage_result.stage_id)
    evaluator_name = None
    if stage_result.evaluated_by_id:
        evaluator = await session.get(User, stage_result.evaluated_by_id)
        evaluator_name = evaluator.full_name if evaluator else None
    return CandidateStageResultRead(
        id=stage_result.id,
        application_id=stage_result.application_id,
        stage_id=stage_result.stage_id,
        stage_name=stage.stage_name if stage else "",
        stage_type=stage.stage_type if stage else "",
        result=stage_result.result,
        score=stage_result.score,
        notes=stage_result.notes,
        test_file_path=stage_result.test_file_path,
        test_file_name=stage_result.test_file_name,
        test_score_raw=stage_result.test_score_raw,
        test_pass_threshold=stage_result.test_pass_threshold,
        evaluated_by_id=stage_result.evaluated_by_id,
        evaluated_by_name=evaluator_name,
        evaluated_at=stage_result.evaluated_at,
        created_at=stage_result.created_at,
        updated_at=stage_result.updated_at,
    )


async def _upsert_stage_result(
    session: AsyncSession,
    application_id: int,
    stage_id: int,
    data: StageResultUpsert,
    user_id: int,
) -> CandidateStageResult:
    result_q = await session.execute(
        select(CandidateStageResult).where(
            CandidateStageResult.application_id == application_id,
            CandidateStageResult.stage_id == stage_id,
        )
    )
    existing = result_q.scalars().first()
    payload = data.model_dump(exclude_unset=True)
    if existing:
        for key, value in payload.items():
            setattr(existing, key, value)
        existing.evaluated_by_id = user_id
        existing.evaluated_at = _utcnow()
        existing.updated_at = _utcnow()
        await session.flush()
        return existing

    created = CandidateStageResult(
        application_id=application_id,
        stage_id=stage_id,
        **payload,
        evaluated_by_id=user_id,
        evaluated_at=_utcnow(),
    )
    session.add(created)
    await session.flush()
    return created


async def list_pipeline_templates(session: AsyncSession) -> list[PipelineStageTemplateRead]:
    rows_q = await session.execute(
        select(PipelineStageTemplate).order_by(PipelineStageTemplate.name, PipelineStageTemplate.id)
    )
    rows = rows_q.scalars().all()
    return [await _template_read(session, row) for row in rows]


async def create_pipeline_template(
    session: AsyncSession,
    data: PipelineStageTemplateCreate,
    created_by_id: int,
) -> PipelineStageTemplateRead:
    _validate_stage_definitions(data.items)
    template = PipelineStageTemplate(
        name=data.name,
        job_position_id=data.job_position_id,
        is_default=data.is_default,
        created_by_id=created_by_id,
    )
    session.add(template)
    await session.flush()
    for item in data.items:
        session.add(PipelineStageTemplateItem(template_id=template.id, **item.model_dump()))
    await session.flush()
    return await _template_read(session, template)


async def update_pipeline_template(
    session: AsyncSession,
    template_id: int,
    data: PipelineStageTemplateUpdate,
) -> PipelineStageTemplateRead:
    template = await _get_template_or_404(session, template_id)
    patch = data.model_dump(exclude_unset=True)
    items = data.items
    patch.pop("items", None)
    for key, value in patch.items():
        setattr(template, key, value)
    if items is not None:
        _validate_stage_definitions(items)
        existing_q = await session.execute(
            select(PipelineStageTemplateItem).where(PipelineStageTemplateItem.template_id == template_id)
        )
        for item in existing_q.scalars().all():
            await session.delete(item)
        await session.flush()
        for item in items:
            session.add(PipelineStageTemplateItem(template_id=template_id, **item.model_dump()))
    await session.flush()
    return await _template_read(session, template)


async def delete_pipeline_template(session: AsyncSession, template_id: int) -> None:
    template = await _get_template_or_404(session, template_id)
    await session.delete(template)
    await session.flush()


async def list_pipeline_for_jr(session: AsyncSession, jr_id: int) -> list[PipelineStageRead]:
    await _get_jr_or_404(session, jr_id)
    rows_q = await session.execute(
        select(PipelineStage)
        .where(PipelineStage.job_requisition_id == jr_id)
        .order_by(PipelineStage.stage_order, PipelineStage.id)
    )
    rows = rows_q.scalars().all()
    return [await _stage_read(session, row) for row in rows]


async def setup_pipeline_for_jr(
    session: AsyncSession,
    jr_id: int,
    data: PipelineSetupRequest,
) -> list[PipelineStageRead]:
    await _get_jr_or_404(session, jr_id)

    existing_results_q = await session.execute(
        select(func.count(CandidateStageResult.id))
        .select_from(PipelineStage)
        .join(CandidateStageResult, CandidateStageResult.stage_id == PipelineStage.id)
        .where(PipelineStage.job_requisition_id == jr_id)
    )
    if existing_results_q.scalar_one():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Không thể cấu hình lại pipeline vì đã có kết quả bước tuyển chọn",
        )

    existing_interviews_q = await session.execute(
        select(func.count(InterviewSession.id))
        .select_from(PipelineStage)
        .join(InterviewSession, InterviewSession.stage_id == PipelineStage.id)
        .where(PipelineStage.job_requisition_id == jr_id)
    )
    if existing_interviews_q.scalar_one():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Không thể cấu hình lại pipeline vì đã có lịch phỏng vấn",
        )

    existing_q = await session.execute(
        select(PipelineStage).where(PipelineStage.job_requisition_id == jr_id)
    )
    for existing in existing_q.scalars().all():
        await session.delete(existing)
    await session.flush()

    stage_defs: list[PipelineStageCreate]
    if data.template_id is not None:
        template = await _get_template_or_404(session, data.template_id)
        items_q = await session.execute(
            select(PipelineStageTemplateItem)
            .where(PipelineStageTemplateItem.template_id == template.id)
            .order_by(PipelineStageTemplateItem.stage_order, PipelineStageTemplateItem.id)
        )
        stage_defs = [
            PipelineStageCreate(
                stage_order=item.stage_order,
                stage_name=item.stage_name,
                stage_type=item.stage_type,
                is_active=True,
            )
            for item in items_q.scalars().all()
        ]
    else:
        stage_defs = data.stages or []

    _validate_stage_definitions(stage_defs)

    created: list[PipelineStage] = []
    for stage_def in sorted(stage_defs, key=lambda item: item.stage_order):
        stage = PipelineStage(job_requisition_id=jr_id, **stage_def.model_dump())
        session.add(stage)
        created.append(stage)
    await session.flush()

    first_stage_type = created[0].stage_type
    new_stage_types = {s.stage_type for s in created}
    # Migrate any application whose current_stage is no longer valid in the new pipeline
    # (includes "new" and any stale stage type from a previous pipeline setup)
    apps_q = await session.execute(
        select(CandidateApplication).where(
            CandidateApplication.job_requisition_id == jr_id,
            CandidateApplication.current_stage.notin_(
                new_stage_types | _TERMINAL_STAGES | {"offer"}
            ),
        )
    )
    for app in apps_q.scalars().all():
        app.current_stage = first_stage_type
        app.updated_at = _utcnow()
    await session.flush()
    return [await _stage_read(session, stage) for stage in created]


async def update_pipeline_stage(
    session: AsyncSession,
    jr_id: int,
    stage_id: int,
    data: PipelineStageUpdate,
) -> PipelineStageRead:
    await _get_jr_or_404(session, jr_id)
    stage = await _get_stage_or_404(session, stage_id)
    if stage.job_requisition_id != jr_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bước pipeline")

    patch = data.model_dump(exclude_unset=True)
    if "stage_order" in patch or "stage_type" in patch:
        stages_q = await session.execute(
            select(PipelineStage).where(
                PipelineStage.job_requisition_id == jr_id,
                PipelineStage.id != stage_id,
            )
        )
        siblings = stages_q.scalars().all()
        next_order = patch.get("stage_order", stage.stage_order)
        next_type = patch.get("stage_type", stage.stage_type)
        if any(item.stage_order == next_order for item in siblings):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="stage_order không được trùng")
        if any(item.stage_type == next_type for item in siblings):
            raise HTTPException(status.HTTP_409_CONFLICT, detail="stage_type không được trùng")

    old_type = stage.stage_type
    for key, value in patch.items():
        setattr(stage, key, value)
    await session.flush()

    if stage.stage_type != old_type:
        apps_q = await session.execute(
            select(CandidateApplication).where(
                CandidateApplication.job_requisition_id == jr_id,
                CandidateApplication.current_stage == old_type,
            )
        )
        for app in apps_q.scalars().all():
            app.current_stage = stage.stage_type
            app.updated_at = _utcnow()

    await session.flush()
    return await _stage_read(session, stage)


async def delete_pipeline_stage(session: AsyncSession, jr_id: int, stage_id: int) -> None:
    await _get_jr_or_404(session, jr_id)
    stage = await _get_stage_or_404(session, stage_id)
    if stage.job_requisition_id != jr_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bước pipeline")

    used_results_q = await session.execute(
        select(func.count()).where(CandidateStageResult.stage_id == stage_id)
    )
    if used_results_q.scalar_one():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Bước pipeline đã có kết quả đánh giá")

    used_interviews_q = await session.execute(
        select(func.count()).where(InterviewSession.stage_id == stage_id)
    )
    if used_interviews_q.scalar_one():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Bước pipeline đã có lịch phỏng vấn")

    apps_q = await session.execute(
        select(func.count()).where(
            CandidateApplication.job_requisition_id == jr_id,
            CandidateApplication.current_stage == stage.stage_type,
        )
    )
    if apps_q.scalar_one():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Có ứng viên đang ở bước pipeline này")

    await session.delete(stage)
    await session.flush()


async def upsert_stage_result(
    session: AsyncSession,
    application_id: int,
    stage_id: int,
    data: StageResultUpsert,
    user_id: int,
) -> CandidateStageResultRead:
    app = await _get_application_or_404(session, application_id)
    stage = await _get_stage_or_404(session, stage_id)
    if stage.job_requisition_id != app.job_requisition_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="stage_id không thuộc JR của application")
    result = await _upsert_stage_result(session, application_id, stage_id, data, user_id)
    return await _result_read(session, result)


async def list_stage_results(session: AsyncSession, application_id: int) -> list[CandidateStageResultRead]:
    await _get_application_or_404(session, application_id)
    rows_q = await session.execute(
        select(CandidateStageResult)
        .where(CandidateStageResult.application_id == application_id)
        .order_by(CandidateStageResult.created_at, CandidateStageResult.id)
    )
    rows = rows_q.scalars().all()
    return [await _result_read(session, row) for row in rows]


_TERMINAL_STAGES = {"rejected", "hired", "withdrawn"}


async def advance_application(
    session: AsyncSession,
    application_id: int,
    data: AdvanceApplicationRequest,
    user_id: int,
) -> ApplicationRead:
    app = await _get_application_or_404(session, application_id)
    if app.current_stage in _TERMINAL_STAGES:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Hồ sơ đã ở trạng thái '{app.current_stage}', không thể thay đổi")
    stage = await _get_stage_or_404(session, data.stage_id)
    if stage.job_requisition_id != app.job_requisition_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="stage_id không thuộc JR của application")
    if stage.stage_type != app.current_stage:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="stage_id không khớp với bước hiện tại của ứng viên")

    await _upsert_stage_result(
        session,
        application_id,
        data.stage_id,
        StageResultUpsert(result=data.result, score=data.score, notes=data.notes),
        user_id,
    )

    if data.result == "pass":
        next_stage_q = await session.execute(
            select(PipelineStage)
            .where(
                PipelineStage.job_requisition_id == app.job_requisition_id,
                PipelineStage.is_active == True,  # noqa: E712
                PipelineStage.stage_order > stage.stage_order,
            )
            .order_by(PipelineStage.stage_order, PipelineStage.id)
            .limit(1)
        )
        next_stage = next_stage_q.scalars().first()
        app.current_stage = next_stage.stage_type if next_stage else "offer"
        app.rejection_reason = None
    elif data.result == "fail":
        if not data.rejection_reason:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Cần nhập lý do loại")
        app.current_stage = "rejected"
        app.rejection_reason = data.rejection_reason
    elif data.result == "hold":
        app.current_stage = stage.stage_type
    elif data.result == "pending":
        app.current_stage = stage.stage_type

    app.updated_at = _utcnow()
    await session.flush()

    # Auto-send email on stage change (non-blocking, never fails pipeline)
    if data.result == "pass" and app.current_stage:
        try:
            from app.services.recruitment_email_service import auto_send_on_stage_change
            await auto_send_on_stage_change(session, application_id, app.current_stage, user_id)
        except Exception:
            pass
    elif data.result == "fail":
        try:
            from app.services.recruitment_email_service import auto_send_on_fail
            await auto_send_on_fail(session, application_id, stage.stage_type, user_id)
        except Exception:
            pass
    elif data.result == "hold":
        try:
            from app.services.recruitment_email_service import auto_send_on_hold
            await auto_send_on_hold(session, application_id, user_id)
        except Exception:
            pass

    return await _application_read(session, app)



async def hold_application(
    session: AsyncSession,
    application_id: int,
    data: HoldApplicationRequest,
    user_id: int,
) -> ApplicationRead:
    app = await _get_application_or_404(session, application_id)
    stage = await _get_stage_or_404(session, data.stage_id)
    if stage.job_requisition_id != app.job_requisition_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="stage_id không thuộc JR của application")

    await _upsert_stage_result(
        session,
        application_id,
        stage.id,
        StageResultUpsert(result="hold", notes=data.notes),
        user_id,
    )
    app.current_stage = stage.stage_type
    app.updated_at = _utcnow()
    await session.flush()

    try:
        from app.services.recruitment_email_service import auto_send_on_hold
        await auto_send_on_hold(session, application_id, user_id)
    except Exception:
        pass

    return await _application_read(session, app)


async def get_kanban(session: AsyncSession, jr_id: int) -> KanbanBoard:
    await _get_jr_or_404(session, jr_id)
    stages_q = await session.execute(
        select(PipelineStage)
        .where(
            PipelineStage.job_requisition_id == jr_id,
            PipelineStage.is_active == True,  # noqa: E712
        )
        .order_by(PipelineStage.stage_order, PipelineStage.id)
    )
    stages = stages_q.scalars().all()

    kanban_stages: list[KanbanStage] = []
    for stage in stages:
        apps_q = await session.execute(
            select(CandidateApplication)
            .where(
                CandidateApplication.job_requisition_id == jr_id,
                CandidateApplication.current_stage == stage.stage_type,
            )
            .order_by(CandidateApplication.applied_date.desc(), CandidateApplication.id.desc())
        )
        cards: list[KanbanCard] = []
        for app in apps_q.scalars().all():
            candidate = await session.get(Candidate, app.candidate_id)
            channel_name = None
            if app.source_channel_id:
                channel = await session.get(RecruitmentChannel, app.source_channel_id)
                channel_name = channel.name if channel else None
            last_result_q = await session.execute(
                select(CandidateStageResult)
                .where(
                    CandidateStageResult.application_id == app.id,
                    CandidateStageResult.stage_id == stage.id,
                )
                .limit(1)
            )
            last_result = last_result_q.scalars().first()
            cards.append(
                KanbanCard(
                    application_id=app.id,
                    candidate_id=app.candidate_id,
                    candidate_name=candidate.full_name if candidate else "",
                    applied_date=app.applied_date,
                    source_channel=channel_name,
                    last_result=last_result.result if last_result else None,
                )
            )

        kanban_stages.append(
            KanbanStage(
                stage=await _stage_read(session, stage),
                applications=cards,
            )
        )

    return KanbanBoard(job_requisition_id=jr_id, stages=kanban_stages)
