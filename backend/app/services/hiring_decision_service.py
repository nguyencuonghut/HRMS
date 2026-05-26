"""Service Quyết định tuyển dụng + Convert to Employee (13.5)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recruitment import (
    CandidateEducation,
    CandidateSkill,
    CandidateWorkExperience,
    HiringDecision,
    Offer,
)
from app.schemas.recruitment import (
    ConvertToEmployeeResult,
    HiringDecisionCreate,
    HiringDecisionRead,
    HiringDecisionUpdate,
)

_HD_STATUS_LABELS = {
    "pending":   "Chờ xử lý",
    "converted": "Đã tạo nhân viên",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _build_read(session: AsyncSession, hd: HiringDecision) -> HiringDecisionRead:
    from app.models.recruitment import Candidate
    from app.models.org import Department, JobPosition, JobTitle

    candidate = await session.get(Candidate, hd.candidate_id)
    dept = await session.get(Department, hd.department_id)
    jp = await session.get(JobPosition, hd.job_position_id)
    jt = await session.get(JobTitle, hd.job_title_id) if hd.job_title_id else None

    return HiringDecisionRead(
        id=hd.id,
        offer_id=hd.offer_id,
        candidate_id=hd.candidate_id,
        candidate_name=candidate.full_name if candidate else f"Candidate #{hd.candidate_id}",
        job_requisition_id=hd.job_requisition_id,
        decision_number=hd.decision_number,
        signed_date=hd.signed_date,
        department_id=hd.department_id,
        department_name=dept.name if dept else f"Dept #{hd.department_id}",
        job_position_id=hd.job_position_id,
        job_position_name=jp.name if jp else f"Position #{hd.job_position_id}",
        job_title_id=hd.job_title_id,
        job_title_name=jt.name if jt else None,
        start_date=hd.start_date,
        probation_salary=hd.probation_salary,
        official_salary=hd.official_salary,
        probation_days=hd.probation_days,
        file_path=hd.file_path,
        file_name=hd.file_name,
        employee_id=hd.employee_id,
        status=hd.status,
        status_label=_HD_STATUS_LABELS.get(hd.status, hd.status),
        created_by_id=hd.created_by_id,
        created_at=hd.created_at,
        updated_at=hd.updated_at,
    )


async def get_decision_for_offer(session: AsyncSession, offer_id: int) -> Optional[HiringDecisionRead]:
    hd = (await session.execute(
        select(HiringDecision).where(HiringDecision.offer_id == offer_id)
    )).scalar_one_or_none()
    if not hd:
        return None
    return await _build_read(session, hd)


async def get_decision(session: AsyncSession, decision_id: int) -> HiringDecisionRead:
    hd = await session.get(HiringDecision, decision_id)
    if not hd:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy quyết định tuyển dụng")
    return await _build_read(session, hd)


async def create_decision(
    session: AsyncSession,
    offer_id: int,
    data: HiringDecisionCreate,
    user_id: int,
) -> HiringDecisionRead:
    offer = await session.get(Offer, offer_id)
    if not offer:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy offer")
    if offer.status != "accepted":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể tạo quyết định tuyển dụng cho offer đã được chấp nhận",
        )

    existing = (await session.execute(
        select(HiringDecision).where(HiringDecision.offer_id == offer_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Offer này đã có quyết định tuyển dụng",
        )

    hd = HiringDecision(
        offer_id=offer_id,
        candidate_id=offer.candidate_id,
        job_requisition_id=offer.job_requisition_id,
        decision_number=data.decision_number,
        signed_date=data.signed_date,
        department_id=data.department_id,
        job_position_id=data.job_position_id,
        job_title_id=data.job_title_id,
        start_date=data.start_date,
        probation_salary=data.probation_salary,
        official_salary=data.official_salary,
        probation_days=data.probation_days,
        status="pending",
        created_by_id=user_id,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    session.add(hd)
    await session.flush()
    return await _build_read(session, hd)


async def update_decision(
    session: AsyncSession,
    decision_id: int,
    data: HiringDecisionUpdate,
    user_id: int,
) -> HiringDecisionRead:
    hd = await session.get(HiringDecision, decision_id)
    if not hd:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy quyết định tuyển dụng")
    if hd.status != "pending":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể chỉnh sửa quyết định ở trạng thái chờ xử lý",
        )
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(hd, field, value)
    hd.updated_at = _utcnow()
    await session.flush()
    return await _build_read(session, hd)


async def convert_to_employee(
    session: AsyncSession,
    decision_id: int,
    user_id: int,
) -> ConvertToEmployeeResult:
    from app.models.recruitment import Candidate, JobRequisition
    from app.models.employee_education import (
        EmployeeEducationHistory,
        EmployeeSkill,
        EmployeeWorkExperience,
    )
    from app.schemas.employee import EmployeeCreate
    from app.services import employee_service, employee_code_service

    hd = await session.get(HiringDecision, decision_id)
    if not hd:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy quyết định tuyển dụng")
    if hd.status == "converted":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Quyết định này đã được chuyển đổi thành nhân viên",
        )
    if hd.status != "pending":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Chỉ có thể chuyển đổi quyết định ở trạng thái chờ xử lý",
        )

    candidate = await session.get(Candidate, hd.candidate_id)
    if not candidate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy thông tin ứng viên")

    _check_required_candidate_fields(candidate)

    # Tính ngày kết thúc thử việc
    from datetime import timedelta
    probation_start = hd.start_date
    probation_end = probation_start + timedelta(days=hd.probation_days)

    payload = EmployeeCreate(
        full_name=candidate.full_name,
        last_name=candidate.last_name or "",
        first_name=candidate.first_name or "",
        date_of_birth=candidate.date_of_birth,
        gender=candidate.gender,
        nationality_id=candidate.nationality_id,
        ethnicity_id=getattr(candidate, "ethnicity_id", None),
        religion_id=getattr(candidate, "religion_id", None),
        id_number=candidate.id_number,
        id_issued_on=candidate.id_issued_on,
        id_issued_by=candidate.id_issued_by or "",
        id_expires_on=getattr(candidate, "id_expires_on", None),
        passport_number=getattr(candidate, "passport_number", None),
        passport_issued_on=getattr(candidate, "passport_issued_on", None),
        passport_expires_on=getattr(candidate, "passport_expires_on", None),
        phone_number=getattr(candidate, "phone_number", None),
        personal_email=getattr(candidate, "email", None),
        status="probation",
        start_date=hd.start_date,
        initial_department_id=hd.department_id,
        initial_job_position_id=hd.job_position_id,
        initial_job_title_id=hd.job_title_id,
        initial_probation_start_date=probation_start,
        initial_probation_end_date=probation_end,
        initial_job_effective_from=hd.start_date,
    )

    emp = await employee_service.create_employee(session, payload)

    # Migrate học vấn
    educations = (await session.execute(
        select(CandidateEducation).where(CandidateEducation.candidate_id == candidate.id)
    )).scalars().all()
    for edu in educations:
        if edu.education_level_id is None:
            continue
        session.add(EmployeeEducationHistory(
            employee_id=emp.id,
            institution_id=edu.institution_id,
            institution_name=edu.institution_name,
            major_id=edu.major_id,
            major_name=edu.major_name,
            education_level_id=edu.education_level_id,
            graduation_year=edu.graduation_year,
            diploma_type=edu.diploma_type,
            is_main_education=edu.is_main_education,
            note=edu.note,
        ))

    # Migrate kinh nghiệm làm việc
    experiences = (await session.execute(
        select(CandidateWorkExperience).where(CandidateWorkExperience.candidate_id == candidate.id)
    )).scalars().all()
    for exp in experiences:
        if exp.start_date is None:
            continue
        session.add(EmployeeWorkExperience(
            employee_id=emp.id,
            company_name=exp.company_name,
            position_name=exp.position_name,
            start_date=exp.start_date,
            end_date=exp.end_date,
            description=exp.description,
        ))

    # Migrate kỹ năng
    skills = (await session.execute(
        select(CandidateSkill).where(CandidateSkill.candidate_id == candidate.id)
    )).scalars().all()
    for sk in skills:
        if sk.skill_id is None:
            continue
        session.add(EmployeeSkill(
            employee_id=emp.id,
            skill_id=sk.skill_id,
            proficiency_level=sk.proficiency_level or "beginner",
            note=sk.note,
        ))

    await session.flush()

    # Cập nhật hiring_decision
    hd.employee_id = emp.id
    hd.status = "converted"
    hd.updated_at = _utcnow()

    # Giảm quantity_remaining của job_requisition, SET completed nếu = 0
    from app.models.recruitment import JobRequisition
    jr = (await session.execute(
        select(JobRequisition)
        .where(JobRequisition.id == hd.job_requisition_id)
        .with_for_update()
    )).scalar_one_or_none()
    if jr and jr.quantity_remaining is not None and jr.quantity_remaining > 0:
        jr.quantity_remaining -= 1
        if jr.quantity_remaining == 0:
            jr.status = "completed"

    await session.flush()

    employee_code = await employee_code_service.build_employee_display_code(session, emp)

    return ConvertToEmployeeResult(
        employee_id=emp.id,
        employee_code=employee_code,
        message=f"Đã tạo nhân viên {emp.full_name} với mã {employee_code}",
    )


def _check_required_candidate_fields(candidate) -> None:
    missing = []
    if not candidate.last_name:
        missing.append("Họ (last_name)")
    if not candidate.first_name:
        missing.append("Tên (first_name)")
    if not candidate.date_of_birth:
        missing.append("Ngày sinh")
    if not candidate.gender:
        missing.append("Giới tính")
    if not candidate.nationality_id:
        missing.append("Quốc tịch")
    if not candidate.id_number:
        missing.append("Số CCCD/CMND")
    if not candidate.id_issued_on:
        missing.append("Ngày cấp CCCD")
    if not candidate.id_issued_by:
        missing.append("Nơi cấp CCCD")
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Hồ sơ ứng viên thiếu thông tin bắt buộc: {', '.join(missing)}",
        )
