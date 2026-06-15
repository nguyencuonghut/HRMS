"""Service Offer & Quyết định tuyển dụng (13.5)."""
from __future__ import annotations

import structlog
from datetime import datetime, timezone

logger = structlog.get_logger(__name__)
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recruitment import CandidateApplication, HiringDecision, JobRequisition, Offer
from app.schemas.recruitment import (
    OfferCreate,
    OfferNegotiateRequest,
    OfferRead,
    OfferRejectRequest,
    OfferStatusLabels,
    OfferUpdate,
)
from app.services.probation_rules import get_probation_legal_group_label, get_probation_limit


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

def _check_probation_salary(probation_salary: Decimal, official_salary: Decimal) -> bool:
    """Returns True nếu lương thử việc thấp hơn 85% lương chính thức (vi phạm)."""
    if official_salary <= 0:
        return False
    return probation_salary < official_salary * Decimal("0.85")


async def _build_offer_read(session: AsyncSession, offer: Offer) -> OfferRead:
    from app.models.recruitment import Candidate
    from app.models.org import Department
    from app.models.org import JobPosition
    from app.models.auth import User

    candidate = await session.get(Candidate, offer.candidate_id)
    candidate_name = candidate.full_name if candidate else f"Candidate #{offer.candidate_id}"

    jp = await session.get(JobPosition, offer.job_position_id) if offer.job_position_id else None
    dept = await session.get(Department, offer.department_id) if offer.department_id else None
    creator = await session.get(User, offer.created_by_id)

    probation_legal_group_code = jp.probation_legal_group if jp else None
    probation_legal_group_label = get_probation_legal_group_label(probation_legal_group_code)
    probation_days_limit = get_probation_limit(probation_legal_group_code)
    probation_limit_configured = probation_days_limit is not None

    return OfferRead(
        id=offer.id,
        application_id=offer.application_id,
        candidate_id=offer.candidate_id,
        candidate_name=candidate_name,
        job_requisition_id=offer.job_requisition_id,
        job_position_id=offer.job_position_id,
        job_position_name=jp.name if jp else None,
        department_id=offer.department_id,
        department_name=dept.name if dept else None,
        proposed_start_date=offer.proposed_start_date,
        probation_salary=offer.probation_salary,
        official_salary=offer.official_salary,
        probation_days=offer.probation_days,
        probation_days_limit=probation_days_limit,
        probation_limit_configured=probation_limit_configured,
        probation_legal_group_code=probation_legal_group_code,
        probation_legal_group_label=probation_legal_group_label,
        probation_salary_warning=_check_probation_salary(offer.probation_salary, offer.official_salary),
        probation_days_warning=probation_days_limit is not None and offer.probation_days > probation_days_limit,
        benefits_note=offer.benefits_note,
        offer_file_path=offer.offer_file_path,
        offer_file_name=offer.offer_file_name,
        status=offer.status,
        status_label=OfferStatusLabels.get(offer.status, offer.status),
        sent_at=offer.sent_at,
        responded_at=offer.responded_at,
        expires_at=offer.expires_at,
        rejection_reason=offer.rejection_reason,
        negotiation_note=offer.negotiation_note,
        internal_note=offer.internal_note,
        created_by_id=offer.created_by_id,
        created_by_name=creator.full_name if creator else None,
        created_at=offer.created_at,
        updated_at=offer.updated_at,
    )


async def list_offers_for_application(
    session: AsyncSession,
    application_id: int,
) -> list[OfferRead]:
    rows = (await session.execute(
        select(Offer)
        .where(Offer.application_id == application_id)
        .order_by(Offer.created_at.desc())
    )).scalars().all()
    return [await _build_offer_read(session, o) for o in rows]


async def get_offer(session: AsyncSession, offer_id: int) -> OfferRead:
    offer = await session.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy offer")
    return await _build_offer_read(session, offer)


async def create_offer(
    session: AsyncSession,
    application_id: int,
    data: OfferCreate,
    user_id: int,
) -> OfferRead:
    application = await session.get(CandidateApplication, application_id)
    if not application:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ ứng tuyển")
    if application.current_stage != "offer":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ được tạo offer khi ứng viên đã ở giai đoạn 'offer'",
        )

    # Kiểm tra đã có offer active chưa (chỉ được 1 offer draft/sent/waiting/negotiating/accepted cùng lúc)
    existing = (await session.execute(
        select(Offer).where(
            Offer.application_id == application_id,
            Offer.status.in_(["draft", "sent", "waiting", "negotiating", "accepted"]),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Hồ sơ này đã có offer đang hoạt động (trạng thái: {existing.status})",
        )

    offer = Offer(
        application_id=application_id,
        candidate_id=application.candidate_id,
        job_requisition_id=application.job_requisition_id,
        job_position_id=data.job_position_id,
        department_id=data.department_id,
        proposed_start_date=data.proposed_start_date,
        probation_salary=data.probation_salary,
        official_salary=data.official_salary,
        probation_days=data.probation_days,
        benefits_note=data.benefits_note,
        expires_at=data.expires_at,
        internal_note=data.internal_note,
        status="draft",
        created_by_id=user_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(offer)
    await session.flush()
    return await _build_offer_read(session, offer)


async def update_offer(
    session: AsyncSession,
    offer_id: int,
    data: OfferUpdate,
    user_id: int,
) -> OfferRead:
    offer = await session.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy offer")
    if offer.status not in ("draft", "negotiating"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể chỉnh sửa offer ở trạng thái nháp hoặc đang đàm phán",
        )
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(offer, field, value)
    offer.updated_at = _utcnow()
    await session.flush()
    return await _build_offer_read(session, offer)


async def send_offer(session: AsyncSession, offer_id: int, user_id: int) -> OfferRead:
    offer = await session.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy offer")
    if offer.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Chỉ có thể gửi offer ở trạng thái nháp")
    offer.status = "sent"
    offer.sent_at = _utcnow()
    offer.updated_at = _utcnow()
    await session.flush()

    try:
        from app.services.recruitment_email_service import auto_send_on_offer_event
        await auto_send_on_offer_event(session, offer.application_id, "offer_sent", user_id)
    except Exception as exc:
        logger.warning("offer_operation_error", error=str(exc))

    return await _build_offer_read(session, offer)


async def accept_offer(session: AsyncSession, offer_id: int, user_id: int) -> OfferRead:
    offer = await session.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy offer")
    if offer.status not in ("sent", "waiting", "negotiating"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể chấp nhận offer đã gửi hoặc đang chờ phản hồi",
        )
    offer.status = "accepted"
    offer.responded_at = _utcnow()
    offer.updated_at = _utcnow()

    # Cập nhật application.current_stage → hired
    application = await session.get(CandidateApplication, offer.application_id)
    if application:
        application.current_stage = "hired"
        application.updated_at = _utcnow()

    await session.flush()

    try:
        from app.services.recruitment_email_service import auto_send_on_offer_event
        await auto_send_on_offer_event(session, offer.application_id, "offer_accepted", user_id)
    except Exception as exc:
        logger.warning("offer_operation_error", error=str(exc))

    return await _build_offer_read(session, offer)


async def reject_offer(
    session: AsyncSession,
    offer_id: int,
    data: OfferRejectRequest,
    user_id: int,
) -> OfferRead:
    offer = await session.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy offer")
    if offer.status not in ("sent", "waiting", "negotiating"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể từ chối offer đã gửi hoặc đang chờ phản hồi",
        )
    offer.status = "rejected"
    offer.rejection_reason = data.rejection_reason
    offer.responded_at = _utcnow()
    offer.updated_at = _utcnow()

    application = await session.get(CandidateApplication, offer.application_id)
    if application:
        application.current_stage = "rejected"
        application.rejection_reason = f"Từ chối offer: {data.rejection_reason}"
        application.updated_at = _utcnow()

    await session.flush()

    try:
        from app.services.recruitment_email_service import auto_send_on_offer_event
        await auto_send_on_offer_event(session, offer.application_id, "offer_rejected", user_id)
    except Exception as exc:
        logger.warning("offer_operation_error", error=str(exc))

    return await _build_offer_read(session, offer)


async def negotiate_offer(
    session: AsyncSession,
    offer_id: int,
    data: OfferNegotiateRequest,
    user_id: int,
) -> OfferRead:
    offer = await session.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy offer")
    if offer.status not in ("sent", "waiting"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể đàm phán offer đã gửi hoặc đang chờ phản hồi",
        )
    offer.status = "negotiating"
    offer.negotiation_note = data.negotiation_note
    offer.updated_at = _utcnow()
    await session.flush()
    return await _build_offer_read(session, offer)
