"""Service cho học vấn, kinh nghiệm, kỹ năng, chứng chỉ, ngoại ngữ (3.4)."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Certificate, EducationLevel, Skill
from app.models.employee_education import (
    EmployeeCertificate,
    EmployeeEducationHistory,
    EmployeeLanguage,
    EmployeeSkill,
    EmployeeWorkExperience,
)
from app.schemas.employee import (
    EducationHistoryCreate,
    EducationHistoryRead,
    EducationHistoryUpdate,
    EmployeeCertificateCreate,
    EmployeeCertificateRead,
    EmployeeCertificateUpdate,
    EmployeeLanguageCreate,
    EmployeeLanguageRead,
    EmployeeLanguageUpdate,
    EmployeeSkillCreate,
    EmployeeSkillRead,
    EmployeeSkillUpdate,
    WorkExperienceCreate,
    WorkExperienceRead,
    WorkExperienceUpdate,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Education Histories ───────────────────────────────────────────────────────

async def _build_edu_read(session: AsyncSession, edu: EmployeeEducationHistory) -> EducationHistoryRead:
    level = await session.get(EducationLevel, edu.education_level_id)
    return EducationHistoryRead(
        id=edu.id,
        employee_id=edu.employee_id,
        institution_id=edu.institution_id,
        institution_name=edu.institution_name,
        major_id=edu.major_id,
        major_name=edu.major_name,
        education_level_id=edu.education_level_id,
        education_level_name=level.name if level else "",
        graduation_year=edu.graduation_year,
        diploma_type=edu.diploma_type,
        is_main_education=edu.is_main_education,
        note=edu.note,
        created_at=edu.created_at,
        updated_at=edu.updated_at,
    )


async def get_education_histories(
    session: AsyncSession, employee_id: int
) -> list[EducationHistoryRead]:
    rows = (
        await session.execute(
            select(EmployeeEducationHistory)
            .where(EmployeeEducationHistory.employee_id == employee_id)
            .order_by(
                EmployeeEducationHistory.is_main_education.desc(),
                EmployeeEducationHistory.graduation_year.desc().nulls_last(),
                EmployeeEducationHistory.created_at.asc(),
            )
        )
    ).scalars().all()
    return [await _build_edu_read(session, r) for r in rows]


async def create_education_history(
    session: AsyncSession,
    employee_id: int,
    payload: EducationHistoryCreate,
) -> EducationHistoryRead:
    edu = EmployeeEducationHistory(
        employee_id=employee_id,
        institution_id=payload.institution_id,
        institution_name=payload.institution_name,
        major_id=payload.major_id,
        major_name=payload.major_name,
        education_level_id=payload.education_level_id,
        graduation_year=payload.graduation_year,
        diploma_type=payload.diploma_type,
        is_main_education=payload.is_main_education,
        note=payload.note,
        created_at=_utcnow(),
    )
    session.add(edu)
    await session.flush()
    return await _build_edu_read(session, edu)


async def _get_edu_or_404(
    session: AsyncSession, employee_id: int, edu_id: int
) -> EmployeeEducationHistory:
    edu = await session.get(EmployeeEducationHistory, edu_id)
    if not edu or edu.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi học vấn")
    return edu


async def update_education_history(
    session: AsyncSession,
    employee_id: int,
    edu_id: int,
    payload: EducationHistoryUpdate,
) -> EducationHistoryRead:
    edu = await _get_edu_or_404(session, employee_id, edu_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(edu, field, value)
    edu.updated_at = _utcnow()
    return await _build_edu_read(session, edu)


async def delete_education_history(
    session: AsyncSession, employee_id: int, edu_id: int
) -> None:
    edu = await _get_edu_or_404(session, employee_id, edu_id)
    await session.delete(edu)


# ── Work Experiences ──────────────────────────────────────────────────────────

async def get_work_experiences(
    session: AsyncSession, employee_id: int
) -> list[EmployeeWorkExperience]:
    rows = (
        await session.execute(
            select(EmployeeWorkExperience)
            .where(EmployeeWorkExperience.employee_id == employee_id)
            .order_by(EmployeeWorkExperience.start_date.desc())
        )
    ).scalars().all()
    return list(rows)


async def create_work_experience(
    session: AsyncSession,
    employee_id: int,
    payload: WorkExperienceCreate,
) -> EmployeeWorkExperience:
    exp = EmployeeWorkExperience(
        employee_id=employee_id,
        company_name=payload.company_name,
        position_name=payload.position_name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        description=payload.description,
        created_at=_utcnow(),
    )
    session.add(exp)
    return exp


async def _get_exp_or_404(
    session: AsyncSession, employee_id: int, exp_id: int
) -> EmployeeWorkExperience:
    exp = await session.get(EmployeeWorkExperience, exp_id)
    if not exp or exp.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kinh nghiệm làm việc")
    return exp


async def update_work_experience(
    session: AsyncSession,
    employee_id: int,
    exp_id: int,
    payload: WorkExperienceUpdate,
) -> EmployeeWorkExperience:
    exp = await _get_exp_or_404(session, employee_id, exp_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(exp, field, value)
    exp.updated_at = _utcnow()
    return exp


async def delete_work_experience(
    session: AsyncSession, employee_id: int, exp_id: int
) -> None:
    exp = await _get_exp_or_404(session, employee_id, exp_id)
    await session.delete(exp)


# ── Skills ────────────────────────────────────────────────────────────────────

async def _build_skill_read(session: AsyncSession, sk: EmployeeSkill) -> EmployeeSkillRead:
    skill_cat = await session.get(Skill, sk.skill_id)
    return EmployeeSkillRead(
        id=sk.id,
        employee_id=sk.employee_id,
        skill_id=sk.skill_id,
        skill_name=skill_cat.name if skill_cat else "",
        skill_group=skill_cat.skill_group if skill_cat else None,
        proficiency_level=sk.proficiency_level,
        note=sk.note,
        created_at=sk.created_at,
        updated_at=sk.updated_at,
    )


async def get_employee_skills(
    session: AsyncSession, employee_id: int
) -> list[EmployeeSkillRead]:
    rows = (
        await session.execute(
            select(EmployeeSkill)
            .where(EmployeeSkill.employee_id == employee_id)
            .order_by(EmployeeSkill.created_at.asc())
        )
    ).scalars().all()
    return [await _build_skill_read(session, r) for r in rows]


async def create_employee_skill(
    session: AsyncSession,
    employee_id: int,
    payload: EmployeeSkillCreate,
) -> EmployeeSkillRead:
    existing = (await session.execute(
        select(EmployeeSkill).where(
            EmployeeSkill.employee_id == employee_id,
            EmployeeSkill.skill_id == payload.skill_id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Nhân viên đã có kỹ năng này")

    sk = EmployeeSkill(
        employee_id=employee_id,
        skill_id=payload.skill_id,
        proficiency_level=payload.proficiency_level,
        note=payload.note,
        created_at=_utcnow(),
    )
    session.add(sk)
    await session.flush()
    return await _build_skill_read(session, sk)


async def _get_skill_or_404(
    session: AsyncSession, employee_id: int, skill_record_id: int
) -> EmployeeSkill:
    sk = await session.get(EmployeeSkill, skill_record_id)
    if not sk or sk.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kỹ năng")
    return sk


async def update_employee_skill(
    session: AsyncSession,
    employee_id: int,
    skill_record_id: int,
    payload: EmployeeSkillUpdate,
) -> EmployeeSkillRead:
    sk = await _get_skill_or_404(session, employee_id, skill_record_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(sk, field, value)
    sk.updated_at = _utcnow()
    return await _build_skill_read(session, sk)


async def delete_employee_skill(
    session: AsyncSession, employee_id: int, skill_record_id: int
) -> None:
    sk = await _get_skill_or_404(session, employee_id, skill_record_id)
    await session.delete(sk)


# ── Certificates ──────────────────────────────────────────────────────────────

async def _build_cert_read(session: AsyncSession, cert: EmployeeCertificate) -> EmployeeCertificateRead:
    cert_cat = await session.get(Certificate, cert.certificate_id)
    return EmployeeCertificateRead(
        id=cert.id,
        employee_id=cert.employee_id,
        certificate_id=cert.certificate_id,
        certificate_name=cert_cat.name if cert_cat else "",
        certificate_number=cert.certificate_number,
        issued_date=cert.issued_date,
        expires_on=cert.expires_on,
        issued_by=cert.issued_by,
        note=cert.note,
        created_at=cert.created_at,
        updated_at=cert.updated_at,
    )


async def get_employee_certificates(
    session: AsyncSession, employee_id: int
) -> list[EmployeeCertificateRead]:
    rows = (
        await session.execute(
            select(EmployeeCertificate)
            .where(EmployeeCertificate.employee_id == employee_id)
            .order_by(EmployeeCertificate.issued_date.desc().nulls_last())
        )
    ).scalars().all()
    return [await _build_cert_read(session, r) for r in rows]


async def create_employee_certificate(
    session: AsyncSession,
    employee_id: int,
    payload: EmployeeCertificateCreate,
) -> EmployeeCertificateRead:
    cert = EmployeeCertificate(
        employee_id=employee_id,
        certificate_id=payload.certificate_id,
        certificate_number=payload.certificate_number,
        issued_date=payload.issued_date,
        expires_on=payload.expires_on,
        issued_by=payload.issued_by,
        note=payload.note,
        created_at=_utcnow(),
    )
    session.add(cert)
    await session.flush()
    return await _build_cert_read(session, cert)


async def _get_cert_or_404(
    session: AsyncSession, employee_id: int, cert_id: int
) -> EmployeeCertificate:
    cert = await session.get(EmployeeCertificate, cert_id)
    if not cert or cert.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy chứng chỉ")
    return cert


async def update_employee_certificate(
    session: AsyncSession,
    employee_id: int,
    cert_id: int,
    payload: EmployeeCertificateUpdate,
) -> EmployeeCertificateRead:
    cert = await _get_cert_or_404(session, employee_id, cert_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cert, field, value)
    cert.updated_at = _utcnow()
    return await _build_cert_read(session, cert)


async def delete_employee_certificate(
    session: AsyncSession, employee_id: int, cert_id: int
) -> None:
    cert = await _get_cert_or_404(session, employee_id, cert_id)
    await session.delete(cert)


# ── Languages ─────────────────────────────────────────────────────────────────

async def get_employee_languages(
    session: AsyncSession, employee_id: int
) -> list[EmployeeLanguage]:
    rows = (
        await session.execute(
            select(EmployeeLanguage)
            .where(EmployeeLanguage.employee_id == employee_id)
            .order_by(EmployeeLanguage.created_at.asc())
        )
    ).scalars().all()
    return list(rows)


async def create_employee_language(
    session: AsyncSession,
    employee_id: int,
    payload: EmployeeLanguageCreate,
) -> EmployeeLanguage:
    existing = (await session.execute(
        select(EmployeeLanguage).where(
            EmployeeLanguage.employee_id == employee_id,
            EmployeeLanguage.language_name == payload.language_name,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Nhân viên đã có ngoại ngữ này")

    lang = EmployeeLanguage(
        employee_id=employee_id,
        language_name=payload.language_name,
        proficiency_level=payload.proficiency_level,
        note=payload.note,
        created_at=_utcnow(),
    )
    session.add(lang)
    return lang


async def _get_lang_or_404(
    session: AsyncSession, employee_id: int, lang_id: int
) -> EmployeeLanguage:
    lang = await session.get(EmployeeLanguage, lang_id)
    if not lang or lang.employee_id != employee_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy ngoại ngữ")
    return lang


async def update_employee_language(
    session: AsyncSession,
    employee_id: int,
    lang_id: int,
    payload: EmployeeLanguageUpdate,
) -> EmployeeLanguage:
    lang = await _get_lang_or_404(session, employee_id, lang_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lang, field, value)
    lang.updated_at = _utcnow()
    return lang


async def delete_employee_language(
    session: AsyncSession, employee_id: int, lang_id: int
) -> None:
    lang = await _get_lang_or_404(session, employee_id, lang_id)
    await session.delete(lang)
