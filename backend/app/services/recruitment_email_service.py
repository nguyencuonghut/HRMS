"""Email template + candidate communication service (Plan 13.7)."""
from __future__ import annotations

import asyncio
import json
import re
import smtplib
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.recruitment import (
    CandidateApplication, CandidateCommunication, RecruitmentEmailTemplate
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class EmailTemplateCreate(BaseModel):
    code: str
    name: str
    trigger_event: Optional[str] = None
    subject: str
    body_html: str
    body_text: Optional[str] = None

class EmailTemplateUpdate(BaseModel):
    name: Optional[str] = None
    trigger_event: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    is_active: Optional[bool] = None

class EmailTemplateRead(BaseModel):
    id: int
    code: str
    name: str
    trigger_event: Optional[str]
    subject: str
    body_html: str
    merge_fields: list[str]
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

class EmailTemplatePreviewRequest(BaseModel):
    candidate_id: Optional[int] = None
    application_id: Optional[int] = None
    use_sample_data: bool = True

class SendEmailRequest(BaseModel):
    template_id: int
    application_id: Optional[int] = None
    custom_subject: Optional[str] = None
    custom_body: Optional[str] = None
    extra_context: Optional[dict] = None

class CommunicationRead(BaseModel):
    id: int
    channel: str
    direction: str
    template_name: Optional[str]
    subject: Optional[str]
    body_html: Optional[str]
    status: str
    sent_at: Optional[datetime]
    sent_by_name: Optional[str]
    trigger_event: Optional[str]
    error_message: Optional[str]
    error_friendly: Optional[str]
    created_at: datetime


# ── Helpers ───────────────────────────────────────────────────────────────────

_FIELD_RE = re.compile(r"\{\{(\w+)\}\}")

def detect_merge_fields(text: str) -> list[str]:
    return list(dict.fromkeys(_FIELD_RE.findall(text)))

def render(template_str: str, context: dict) -> str:
    def replacer(m):
        return str(context.get(m.group(1), m.group(0)))
    return _FIELD_RE.sub(replacer, template_str)

def _friendly_error(msg: Optional[str]) -> Optional[str]:
    if not msg:
        return None
    m = msg.lower()
    if "không có email" in m or "no email" in m:
        return "Ứng viên chưa có địa chỉ email. Vui lòng cập nhật thông tin ứng viên trước khi gửi."
    if "connection refused" in m or "connect" in m and "refused" in m:
        return "Không kết nối được đến máy chủ email (SMTP). Kiểm tra lại cấu hình SMTP hoặc liên hệ quản trị viên hệ thống."
    if "timeout" in m or "timed out" in m:
        return "Hết thời gian chờ khi kết nối đến máy chủ email. Có thể máy chủ SMTP đang quá tải hoặc bị chặn tường lửa."
    if "authentication" in m or "535" in m or "534" in m or "username and password" in m:
        return "Xác thực SMTP thất bại. Tên đăng nhập hoặc mật khẩu email không đúng. Liên hệ quản trị viên để kiểm tra cấu hình."
    if "550" in m or "relay" in m:
        return "Máy chủ email từ chối gửi. Địa chỉ email ứng viên có thể không tồn tại hoặc bị từ chối bởi máy chủ nhận."
    if "ssl" in m or "tls" in m or "certificate" in m:
        return "Lỗi bảo mật kết nối SMTP (SSL/TLS). Kiểm tra lại cài đặt mã hóa email trong cấu hình hệ thống."
    if "getaddrinfo" in m or "name or service not known" in m or "nodename nor servname" in m:
        return "Không tìm thấy địa chỉ máy chủ email. Kiểm tra lại tên miền SMTP trong cấu hình hệ thống."
    if "smtplib" in m or "smtp" in m:
        return "Lỗi giao tiếp với máy chủ email. Liên hệ quản trị viên hệ thống để kiểm tra cấu hình SMTP."
    return "Gửi email thất bại do lỗi không xác định. Liên hệ quản trị viên hệ thống để được hỗ trợ."


def _parse_fields(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        return json.loads(raw)
    except Exception:
        return []

def _to_template_read(t: RecruitmentEmailTemplate) -> EmailTemplateRead:
    return EmailTemplateRead(
        id=t.id,
        code=t.code,
        name=t.name,
        trigger_event=t.trigger_event,
        subject=t.subject,
        body_html=t.body_html,
        merge_fields=_parse_fields(t.merge_fields),
        is_active=t.is_active,
        is_system=t.is_system,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )

async def _build_comm_read(session: AsyncSession, comm: CandidateCommunication) -> CommunicationRead:
    template_name = None
    if comm.template_id:
        tmpl = await session.get(RecruitmentEmailTemplate, comm.template_id)
        if tmpl:
            template_name = tmpl.name

    sent_by_name = None
    if comm.sent_by_id:
        from app.models.auth import User
        user = await session.get(User, comm.sent_by_id)
        if user:
            sent_by_name = user.full_name

    return CommunicationRead(
        id=comm.id,
        channel=comm.channel,
        direction=comm.direction,
        template_name=template_name,
        subject=comm.subject,
        body_html=comm.body_html,
        status=comm.status,
        sent_at=comm.sent_at,
        sent_by_name=sent_by_name,
        trigger_event=comm.trigger_event,
        error_message=comm.error_message if comm.status == "failed" else None,
        error_friendly=_friendly_error(comm.error_message) if comm.status == "failed" else None,
        created_at=comm.created_at,
    )


# ── Template CRUD ─────────────────────────────────────────────────────────────

async def list_templates(session: AsyncSession, active_only: bool = False) -> list[EmailTemplateRead]:
    q = select(RecruitmentEmailTemplate).order_by(RecruitmentEmailTemplate.id)
    if active_only:
        q = q.where(RecruitmentEmailTemplate.is_active == True)
    rows = (await session.execute(q)).scalars().all()
    return [_to_template_read(r) for r in rows]

async def get_template(session: AsyncSession, template_id: int) -> EmailTemplateRead:
    t = await session.get(RecruitmentEmailTemplate, template_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy email template")
    return _to_template_read(t)

async def create_template(session: AsyncSession, data: EmailTemplateCreate, user_id: int) -> EmailTemplateRead:
    existing = (await session.execute(
        select(RecruitmentEmailTemplate).where(RecruitmentEmailTemplate.code == data.code)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Mã template đã tồn tại")
    fields = detect_merge_fields(data.subject + data.body_html)
    t = RecruitmentEmailTemplate(
        code=data.code,
        name=data.name,
        trigger_event=data.trigger_event,
        subject=data.subject,
        body_html=data.body_html,
        body_text=data.body_text,
        merge_fields=json.dumps(fields),
        is_active=True,
        is_system=False,
        created_by_id=user_id,
    )
    session.add(t)
    await session.flush()
    return _to_template_read(t)

async def update_template(session: AsyncSession, template_id: int, data: EmailTemplateUpdate) -> EmailTemplateRead:
    t = await session.get(RecruitmentEmailTemplate, template_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy email template")
    if t.is_system:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Không thể sửa template hệ thống")
    for field, val in data.model_dump(exclude_none=True).items():
        setattr(t, field, val)
    if data.subject is not None or data.body_html is not None:
        combined = (data.subject or t.subject) + (data.body_html or t.body_html)
        t.merge_fields = json.dumps(detect_merge_fields(combined))
    t.updated_at = _utcnow()
    await session.flush()
    return _to_template_read(t)

async def delete_template(session: AsyncSession, template_id: int) -> None:
    t = await session.get(RecruitmentEmailTemplate, template_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy email template")
    if t.is_system:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Không thể xóa template hệ thống")
    await session.delete(t)
    await session.flush()


# ── Context builder ───────────────────────────────────────────────────────────

_SAMPLE_CONTEXT = {
    "ten_ung_vien": "Nguyễn Văn A",
    "ho_ung_vien": "Nguyễn",
    "vi_tri": "Chuyên viên Kế toán",
    "phong_ban": "Phòng Kế toán",
    "ten_cong_ty": settings.COMPANY_NAME,
    "ngay_phong_van": "15/06/2026",
    "gio_phong_van": "09:00",
    "dia_diem_phong_van": "Tầng 3, 123 Đường ABC, Hà Nội",
    "ten_hr": "Nguyễn Thị HR",
    "email_hr": "hr@company.com",
    "sdt_hr": "0901234567",
    "ngay_bat_dau": "01/07/2026",
    "luong_thu_viec": "8.500.000 ₫",
    "thoi_gian_thu_viec": "60 ngày",
    "han_phan_hoi_offer": "30/06/2026",
}

async def build_context(
    session: AsyncSession,
    candidate_id: Optional[int] = None,
    application_id: Optional[int] = None,
    sender_user_id: Optional[int] = None,
) -> dict:
    ctx: dict = {"ten_cong_ty": settings.COMPANY_NAME}

    if candidate_id:
        from app.models.recruitment import Candidate
        cand = await session.get(Candidate, candidate_id)
        if cand:
            ctx["ten_ung_vien"] = cand.full_name or ""
            name_parts = (cand.full_name or "").split()
            ctx["ho_ung_vien"] = name_parts[0] if name_parts else ""

    if application_id:
        app = await session.get(CandidateApplication, application_id)
        if app:
            from app.models.recruitment import JobRequisition, Candidate
            from app.models.org import Department, JobPosition
            jr = await session.get(JobRequisition, app.job_requisition_id)
            if jr:
                if jr.job_position_id:
                    jp = await session.get(JobPosition, jr.job_position_id)
                    if jp:
                        ctx["vi_tri"] = jp.name
                if jr.department_id:
                    dept = await session.get(Department, jr.department_id)
                    if dept:
                        ctx["phong_ban"] = dept.name

            if not candidate_id:
                cand = await session.get(Candidate, app.candidate_id)
                if cand:
                    ctx["ten_ung_vien"] = cand.full_name or ""
                    name_parts = (cand.full_name or "").split()
                    ctx["ho_ung_vien"] = name_parts[0] if name_parts else ""

            # Latest interview session
            from app.models.recruitment import InterviewSession
            intvw_q = (await session.execute(
                select(InterviewSession)
                .where(InterviewSession.application_id == application_id)
                .order_by(InterviewSession.scheduled_at.desc())
                .limit(1)
            )).scalar_one_or_none()
            if intvw_q and intvw_q.scheduled_at:
                _gmt7 = timezone(timedelta(hours=7))
                _local = intvw_q.scheduled_at.replace(tzinfo=timezone.utc).astimezone(_gmt7)
                ctx["ngay_phong_van"] = _local.strftime("%d/%m/%Y")
                ctx["gio_phong_van"] = _local.strftime("%H:%M")
                ctx["dia_diem_phong_van"] = intvw_q.location or ""

            # Offer
            from app.models.recruitment import Offer
            offer_q = (await session.execute(
                select(Offer)
                .where(Offer.application_id == application_id)
                .order_by(Offer.created_at.desc())
                .limit(1)
            )).scalar_one_or_none()
            if offer_q:
                ctx["luong_thu_viec"] = f"{float(offer_q.probation_salary):,.0f} ₫".replace(",", ".")
                ctx["thoi_gian_thu_viec"] = f"{offer_q.probation_days} ngày"
                if offer_q.expires_at:
                    ctx["han_phan_hoi_offer"] = offer_q.expires_at.strftime("%d/%m/%Y")
                if offer_q.proposed_start_date:
                    ctx["ngay_bat_dau"] = offer_q.proposed_start_date.strftime("%d/%m/%Y")

    if sender_user_id:
        from app.models.auth import User
        sender = await session.get(User, sender_user_id)
        if sender:
            ctx["ten_hr"] = getattr(sender, "full_name", "") or ""
            ctx["email_hr"] = getattr(sender, "email", "") or ""
            ctx["sdt_hr"] = getattr(sender, "phone_number", "") or ""

    return ctx


# ── Preview ───────────────────────────────────────────────────────────────────

async def preview_template(
    session: AsyncSession,
    template_id: int,
    req: EmailTemplatePreviewRequest,
    user_id: int,
) -> tuple[str, str]:
    t = await session.get(RecruitmentEmailTemplate, template_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy email template")

    has_real_context = req.candidate_id or req.application_id
    if req.use_sample_data or not has_real_context:
        ctx = {**_SAMPLE_CONTEXT}
    else:
        ctx = await build_context(
            session,
            candidate_id=req.candidate_id,
            application_id=req.application_id,
            sender_user_id=user_id,
        )

    return render(t.subject, ctx), render(t.body_html, ctx)


# ── SMTP send ─────────────────────────────────────────────────────────────────

def _smtp_send_sync(to_email: str, subject: str, body_html: str, body_text: Optional[str]) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((str(Header(settings.SMTP_FROM_NAME, "utf-8")), settings.SMTP_FROM_EMAIL))
    msg["To"] = to_email
    if body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    if settings.SMTP_USE_TLS:
        # Direct SSL — typically port 465
        server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        server.ehlo()
    else:
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10)
        server.ehlo()
        if settings.SMTP_USE_STARTTLS:
            server.starttls()
            server.ehlo()  # re-advertise capabilities after TLS handshake
    if settings.SMTP_USERNAME:
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
    server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
    server.quit()


# ── Communication log ─────────────────────────────────────────────────────────

async def send_email(
    session: AsyncSession,
    candidate_id: int,
    req: SendEmailRequest,
    user_id: int,
    trigger_event: Optional[str] = None,
    auto_send: bool = False,
) -> CommunicationRead:
    from app.models.recruitment import Candidate
    cand = await session.get(Candidate, candidate_id)
    if not cand:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy ứng viên")

    t = await session.get(RecruitmentEmailTemplate, req.template_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy email template")

    ctx = await build_context(
        session,
        candidate_id=candidate_id,
        application_id=req.application_id,
        sender_user_id=user_id,
    )
    if req.extra_context:
        ctx.update(req.extra_context)

    subject = render(req.custom_subject or t.subject, ctx)
    body_html = render(req.custom_body or t.body_html, ctx)
    body_text = render(t.body_text or "", ctx) or None

    comm = CandidateCommunication(
        candidate_id=candidate_id,
        application_id=req.application_id,
        channel="email",
        direction="outbound",
        template_id=req.template_id,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        status="pending",
        trigger_event=trigger_event,
        merge_context=json.dumps(ctx),
        sent_by_id=None if auto_send else user_id,
    )
    session.add(comm)
    await session.flush()

    to_email = cand.personal_email or ""
    if not to_email:
        comm.status = "failed"
        comm.error_message = "Ứng viên không có email"
        await session.flush()
        return await _build_comm_read(session, comm)

    # Send in thread pool (non-blocking)
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _smtp_send_sync, to_email, subject, body_html, body_text)
        comm.status = "sent"
        comm.sent_at = _utcnow()
    except Exception as exc:
        comm.status = "failed"
        comm.error_message = str(exc)[:500]

    await session.flush()
    return await _build_comm_read(session, comm)


async def get_candidate_communications(
    session: AsyncSession, candidate_id: int
) -> list[CommunicationRead]:
    rows = (await session.execute(
        select(CandidateCommunication)
        .where(CandidateCommunication.candidate_id == candidate_id)
        .order_by(CandidateCommunication.created_at.desc())
    )).scalars().all()
    result = []
    for comm in rows:
        result.append(await _build_comm_read(session, comm))
    return result


async def get_application_communications(
    session: AsyncSession, application_id: int
) -> list[CommunicationRead]:
    rows = (await session.execute(
        select(CandidateCommunication)
        .where(CandidateCommunication.application_id == application_id)
        .order_by(CandidateCommunication.created_at.desc())
    )).scalars().all()
    result = []
    for comm in rows:
        result.append(await _build_comm_read(session, comm))
    return result


async def auto_send_on_stage_change(
    session: AsyncSession,
    application_id: int,
    new_stage: str,
    user_id: int,
) -> None:
    trigger_event = f"stage_moved:{new_stage}"
    tmpl = (await session.execute(
        select(RecruitmentEmailTemplate)
        .where(
            RecruitmentEmailTemplate.trigger_event == trigger_event,
            RecruitmentEmailTemplate.is_active == True,
        )
        .limit(1)
    )).scalar_one_or_none()
    if not tmpl:
        return

    app = await session.get(CandidateApplication, application_id)
    if not app:
        return

    from app.models.recruitment import Candidate
    cand = await session.get(Candidate, app.candidate_id)
    if not cand or not cand.personal_email:
        return

    try:
        await send_email(
            session,
            candidate_id=app.candidate_id,
            req=SendEmailRequest(template_id=tmpl.id, application_id=application_id),
            user_id=user_id,
            trigger_event=trigger_event,
            auto_send=True,
        )
    except Exception:
        pass  # never rollback pipeline for email failure


async def auto_send_on_offer_event(
    session: AsyncSession,
    application_id: int,
    event: str,
    user_id: int,
) -> None:
    tmpl = (await session.execute(
        select(RecruitmentEmailTemplate)
        .where(
            RecruitmentEmailTemplate.trigger_event == event,
            RecruitmentEmailTemplate.is_active == True,
        )
        .limit(1)
    )).scalar_one_or_none()
    if not tmpl:
        return

    app = await session.get(CandidateApplication, application_id)
    if not app:
        return

    from app.models.recruitment import Candidate
    cand = await session.get(Candidate, app.candidate_id)
    if not cand or not cand.personal_email:
        return

    try:
        await send_email(
            session,
            candidate_id=app.candidate_id,
            req=SendEmailRequest(template_id=tmpl.id, application_id=application_id),
            user_id=user_id,
            trigger_event=event,
            auto_send=True,
        )
    except Exception:
        pass


async def auto_send_on_hold(
    session: AsyncSession,
    application_id: int,
    user_id: int,
) -> None:
    """Fires when a candidate is placed on hold — notifies them that their application is under review."""
    trigger_event = "hold"
    tmpl = (await session.execute(
        select(RecruitmentEmailTemplate)
        .where(
            RecruitmentEmailTemplate.trigger_event == trigger_event,
            RecruitmentEmailTemplate.is_active == True,
        )
        .limit(1)
    )).scalar_one_or_none()
    if not tmpl:
        return

    app = await session.get(CandidateApplication, application_id)
    if not app:
        return

    from app.models.recruitment import Candidate
    cand = await session.get(Candidate, app.candidate_id)
    if not cand or not cand.personal_email:
        return

    try:
        await send_email(
            session,
            candidate_id=app.candidate_id,
            req=SendEmailRequest(template_id=tmpl.id, application_id=application_id),
            user_id=user_id,
            trigger_event=trigger_event,
            auto_send=True,
        )
    except Exception:
        pass


_STAGES_WITH_INTERVIEW_REJECTION = {"interview", "final"}


async def auto_send_on_fail(
    session: AsyncSession,
    application_id: int,
    rejected_from_stage_type: str,
    user_id: int,
) -> None:
    """Pick rejection template based on which stage the candidate was rejected from.

    interview/final → 'rejected' (rejection_after_interview)
    earlier stages  → 'stage_moved:rejected' (rejection_early)
    """
    trigger_event = (
        "rejected"
        if rejected_from_stage_type in _STAGES_WITH_INTERVIEW_REJECTION
        else "stage_moved:rejected"
    )
    tmpl = (await session.execute(
        select(RecruitmentEmailTemplate)
        .where(
            RecruitmentEmailTemplate.trigger_event == trigger_event,
            RecruitmentEmailTemplate.is_active == True,
        )
        .limit(1)
    )).scalar_one_or_none()
    if not tmpl:
        return

    app = await session.get(CandidateApplication, application_id)
    if not app:
        return

    from app.models.recruitment import Candidate
    cand = await session.get(Candidate, app.candidate_id)
    if not cand or not cand.personal_email:
        return

    try:
        await send_email(
            session,
            candidate_id=app.candidate_id,
            req=SendEmailRequest(template_id=tmpl.id, application_id=application_id),
            user_id=user_id,
            trigger_event=trigger_event,
            auto_send=True,
        )
    except Exception:
        pass


async def auto_send_on_interview_scheduled(
    session: AsyncSession,
    application_id: int,
    user_id: int,
) -> None:
    """Fires after an InterviewSession is created — context has real time/location."""
    trigger_event = "interview_scheduled"
    tmpl = (await session.execute(
        select(RecruitmentEmailTemplate)
        .where(
            RecruitmentEmailTemplate.trigger_event == trigger_event,
            RecruitmentEmailTemplate.is_active == True,
        )
        .limit(1)
    )).scalar_one_or_none()
    if not tmpl:
        return

    app = await session.get(CandidateApplication, application_id)
    if not app:
        return

    from app.models.recruitment import Candidate
    cand = await session.get(Candidate, app.candidate_id)
    if not cand or not cand.personal_email:
        return

    try:
        await send_email(
            session,
            candidate_id=app.candidate_id,
            req=SendEmailRequest(template_id=tmpl.id, application_id=application_id),
            user_id=user_id,
            trigger_event=trigger_event,
            auto_send=True,
        )
    except Exception:
        pass
