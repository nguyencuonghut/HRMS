"""Service hồ sơ ứng viên (13.3)."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import (
    EducationLevel,
    EducationMajor,
    EducationalInstitution,
    Ethnicity,
    Nationality,
    Religion,
)
from app.models.auth import User
from app.models.org import Department, JobPosition
from app.models.recruitment import (
    Candidate,
    CandidateApplication,
    CandidateAttachment,
    CandidateEducation,
    CandidateSkill,
    CandidateWorkExperience,
    JobRequisition,
    PipelineStage,
    RecruitmentChannel,
)
from app.services.administrative_import_service import normalize_text
from app.schemas.recruitment import (
    ApplicationCreate,
    ApplicationListPage,
    ApplicationRead,
    AttachmentTypeLabels,
    CandidateAttachmentRead,
    CandidateCreate,
    CandidateDuplicateCheck,
    CandidateDuplicateCheckResult,
    CandidateDuplicateMatch,
    CandidateDuplicateReasonLabels,
    CandidateEducationCreate,
    CandidateEducationRead,
    CandidateGenderLabels,
    CandidateListItem,
    CandidateListPage,
    CandidateRead,
    CandidateSkillCreate,
    CandidateSkillRead,
    CandidateUpdate,
    CandidateWorkExpCreate,
    CandidateWorkExpRead,
    IdentityStrengthLabels,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_candidate_or_404(session: AsyncSession, candidate_id: int) -> Candidate:
    c = await session.get(Candidate, candidate_id)
    if not c or not c.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy ứng viên")
    return c


def _att_read(att: CandidateAttachment) -> CandidateAttachmentRead:
    return CandidateAttachmentRead(
        id=att.id,
        candidate_id=att.candidate_id,
        attachment_type=att.attachment_type,
        attachment_type_label=AttachmentTypeLabels.get(att.attachment_type, att.attachment_type),
        file_name=att.file_name,
        file_size=att.file_size,
        mime_type=att.mime_type,
        note=att.note,
        uploaded_at=att.uploaded_at,
        download_url=f"/api/v1/recruitment/candidates/{att.candidate_id}/attachments/{att.id}/download",
    )


def _split_full_name(full_name: str) -> tuple[Optional[str], Optional[str]]:
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return None, None
    if len(parts) == 1:
        return None, parts[0]
    return " ".join(parts[:-1]), parts[-1]


def _normalize_name(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return normalize_text(value)


def _normalize_email(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    return normalized or None


def _normalize_digits(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return digits or None


def _normalize_document(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = re.sub(r"[\s.\-]", "", value).upper()
    return normalized or None


async def _resolve_education_refs(
    session: AsyncSession,
    payload: CandidateEducationCreate,
) -> tuple[EducationalInstitution, Optional[EducationMajor], EducationLevel]:
    institution = await session.get(EducationalInstitution, payload.institution_id)
    if not institution or not institution.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Trường học không hợp lệ")

    major = None
    if payload.major_id is not None:
        major = await session.get(EducationMajor, payload.major_id)
        if not major or not major.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Chuyên ngành không hợp lệ")

    level = await session.get(EducationLevel, payload.education_level_id)
    if not level or not level.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Trình độ học vấn không hợp lệ")

    return institution, major, level


def _edu_read(
    edu: CandidateEducation,
    level_name: Optional[str],
) -> CandidateEducationRead:
    return CandidateEducationRead(
        id=edu.id,
        candidate_id=edu.candidate_id,
        institution_id=edu.institution_id,
        institution_name=edu.institution_name,
        major_id=edu.major_id,
        major_name=edu.major_name,
        education_level_id=edu.education_level_id,
        education_level_name=level_name,
        graduation_year=edu.graduation_year,
        diploma_type=edu.diploma_type,
        is_main_education=edu.is_main_education,
        note=edu.note,
    )


async def _resolve_nationality_id(
    session: AsyncSession,
    nationality_id: Optional[int],
    raw_nationality_text: Optional[str],
) -> Optional[int]:
    if nationality_id:
        return nationality_id
    if not raw_nationality_text:
        return None
    normalized = normalize_text(raw_nationality_text)
    result = await session.execute(
        select(Nationality.id).where(
            or_(
                Nationality.normalized_name == normalized,
                func.lower(Nationality.code) == normalized,
                func.lower(Nationality.iso2_code) == normalized,
                func.lower(Nationality.iso3_code) == normalized,
            )
        )
    )
    return result.scalar_one_or_none()


def _candidate_duplicate_reasons(
    candidate: Candidate,
    payload: CandidateDuplicateCheck,
) -> tuple[list[str], list[str]]:
    exact_reason_codes: list[str] = []
    possible_reason_codes: list[str] = []

    normalized_id_number = _normalize_document(payload.id_number)
    normalized_passport_number = _normalize_document(payload.passport_number)
    normalized_phone_number = _normalize_digits(payload.phone_number)
    normalized_personal_email = _normalize_email(payload.personal_email)
    normalized_full_name = _normalize_name(payload.full_name)
    candidate_full_name = _normalize_name(candidate.full_name)

    if normalized_id_number and _normalize_document(candidate.id_number) == normalized_id_number:
        exact_reason_codes.append("same_id_number")

    if normalized_passport_number and _normalize_document(candidate.passport_number) == normalized_passport_number:
        exact_reason_codes.append("same_passport_number")

    if normalized_personal_email and _normalize_email(candidate.personal_email) == normalized_personal_email:
        exact_reason_codes.append("same_personal_email")

    if normalized_phone_number and _normalize_digits(candidate.phone_number) == normalized_phone_number:
        exact_reason_codes.append("same_phone_number")

    if normalized_full_name and candidate_full_name == normalized_full_name:
        if payload.date_of_birth and candidate.date_of_birth == payload.date_of_birth:
            possible_reason_codes.append("same_full_name_and_date_of_birth")
        else:
            possible_reason_codes.append("same_full_name")

    return exact_reason_codes, possible_reason_codes


def _build_duplicate_match(
    candidate: Candidate,
    match_level: str,
    reason_codes: list[str],
) -> CandidateDuplicateMatch:
    return CandidateDuplicateMatch(
        candidate_id=candidate.id,
        full_name=candidate.full_name,
        date_of_birth=candidate.date_of_birth,
        id_number=candidate.id_number,
        passport_number=candidate.passport_number,
        phone_number=candidate.phone_number,
        personal_email=candidate.personal_email,
        current_company=candidate.current_company,
        current_position=candidate.current_position,
        match_level=match_level,
        reason_codes=reason_codes,
        reason_labels=[
            CandidateDuplicateReasonLabels.get(reason_code, reason_code)
            for reason_code in reason_codes
        ],
    )


def _conversion_missing_fields(candidate: Candidate) -> list[str]:
    required = {
        "last_name": candidate.last_name,
        "first_name": candidate.first_name,
        "date_of_birth": candidate.date_of_birth,
        "gender": candidate.gender,
        "nationality_id": candidate.nationality_id,
        "id_number": candidate.id_number,
        "id_issued_on": candidate.id_issued_on,
        "id_issued_by": candidate.id_issued_by,
    }
    return [field_name for field_name, value in required.items() if value in (None, "")]


def _identity_strength(candidate: Candidate) -> str:
    if candidate.id_number or candidate.passport_number:
        return "strong"
    if candidate.personal_email or candidate.phone_number or (candidate.full_name and candidate.date_of_birth):
        return "medium"
    return "weak"


async def _build_read(session: AsyncSession, c: Candidate) -> CandidateRead:
    # Load sub-resources
    edus_q = await session.execute(
        select(CandidateEducation).where(CandidateEducation.candidate_id == c.id)
    )
    edus = edus_q.scalars().all()

    exps_q = await session.execute(
        select(CandidateWorkExperience)
        .where(CandidateWorkExperience.candidate_id == c.id)
        .order_by(CandidateWorkExperience.sort_order, CandidateWorkExperience.id)
    )
    exps = exps_q.scalars().all()

    skills_q = await session.execute(
        select(CandidateSkill).where(CandidateSkill.candidate_id == c.id)
    )
    skills = skills_q.scalars().all()

    atts_q = await session.execute(
        select(CandidateAttachment)
        .where(CandidateAttachment.candidate_id == c.id)
        .order_by(CandidateAttachment.uploaded_at.desc())
    )
    atts = atts_q.scalars().all()

    # Count active applications
    app_count_q = await session.execute(
        select(func.count()).where(
            CandidateApplication.candidate_id == c.id,
            CandidateApplication.current_stage.not_in(["hired", "rejected", "withdrawn"]),
        )
    )
    active_apps = app_count_q.scalar_one()

    # Education level names
    edu_reads: list[CandidateEducationRead] = []
    for edu in edus:
        level_name = None
        if edu.education_level_id:
            lv = await session.get(EducationLevel, edu.education_level_id)
            level_name = lv.name if lv else None
        edu_reads.append(_edu_read(edu, level_name))

    nationality_name = ethnicity_name = religion_name = None
    if c.nationality_id:
        nationality = await session.get(Nationality, c.nationality_id)
        nationality_name = nationality.name if nationality else None
    if c.ethnicity_id:
        ethnicity = await session.get(Ethnicity, c.ethnicity_id)
        ethnicity_name = ethnicity.name if ethnicity else None
    if c.religion_id:
        religion = await session.get(Religion, c.religion_id)
        religion_name = religion.name if religion else None

    # Channel name
    channel_name = None
    if c.source_channel_id:
        ch = await session.get(RecruitmentChannel, c.source_channel_id)
        channel_name = ch.name if ch else None

    # Creator name
    created_by_name = None
    if c.created_by_id:
        u = await session.get(User, c.created_by_id)
        created_by_name = u.full_name if u else None

    missing_fields = _conversion_missing_fields(c)
    identity_strength = _identity_strength(c)

    return CandidateRead(
        id=c.id,
        full_name=c.full_name,
        last_name=c.last_name,
        first_name=c.first_name,
        date_of_birth=c.date_of_birth,
        gender=c.gender,
        gender_label=CandidateGenderLabels.get(c.gender) if c.gender else None,
        nationality_id=c.nationality_id,
        nationality_name=nationality_name,
        raw_nationality_text=c.raw_nationality_text,
        ethnicity_id=c.ethnicity_id,
        ethnicity_name=ethnicity_name,
        religion_id=c.religion_id,
        religion_name=religion_name,
        id_number=c.id_number,
        id_issued_on=c.id_issued_on,
        id_issued_by=c.id_issued_by,
        id_expires_on=c.id_expires_on,
        passport_number=c.passport_number,
        passport_issued_on=c.passport_issued_on,
        passport_expires_on=c.passport_expires_on,
        work_permit_number=c.work_permit_number,
        work_permit_issued_on=c.work_permit_issued_on,
        work_permit_expires_on=c.work_permit_expires_on,
        phone_number=c.phone_number,
        personal_email=c.personal_email,
        personal_tax_code=c.personal_tax_code,
        bhxh_code=c.bhxh_code,
        address=c.address,
        current_company=c.current_company,
        current_position=c.current_position,
        expected_salary=c.expected_salary,
        source_channel_id=c.source_channel_id,
        source_channel_name=channel_name,
        source_note=c.source_note,
        internal_note=c.internal_note,
        tags=c.tags or [],
        is_active=c.is_active,
        educations=edu_reads,
        work_experiences=[
            CandidateWorkExpRead(
                id=e.id,
                candidate_id=e.candidate_id,
                company_name=e.company_name,
                position_name=e.position_name,
                start_date=e.start_date,
                end_date=e.end_date,
                description=e.description,
                sort_order=e.sort_order,
            )
            for e in exps
        ],
        skills=[
            CandidateSkillRead(
                id=s.id,
                candidate_id=s.candidate_id,
                skill_name=s.skill_name,
                proficiency_level=s.proficiency_level,
            )
            for s in skills
        ],
        attachments=[_att_read(a) for a in atts],
        active_applications=active_apps,
        identity_strength=identity_strength,
        identity_strength_label=IdentityStrengthLabels[identity_strength],
        conversion_ready=not missing_fields,
        conversion_missing_fields=missing_fields,
        created_by_name=created_by_name,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────


async def list_candidates(
    session: AsyncSession,
    search: Optional[str],
    source_channel_id: Optional[int],
    page: int,
    page_size: int,
) -> CandidateListPage:
    base = select(Candidate).where(Candidate.is_active == True)  # noqa: E712

    if source_channel_id:
        base = base.where(Candidate.source_channel_id == source_channel_id)

    if search:
        term = search.strip()
        ts_query = func.plainto_tsquery("simple", term)
        ts_vec = func.to_tsvector("simple", Candidate.full_name)
        base = base.where(
            or_(
                ts_vec.op("@@")(ts_query),
                Candidate.personal_email.ilike(f"%{term}%"),
                Candidate.phone_number.ilike(f"%{term}%"),
            )
        )

    total_q = await session.execute(select(func.count()).select_from(base.subquery()))
    total = total_q.scalar_one()

    rows_q = await session.execute(
        base.order_by(Candidate.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = rows_q.scalars().all()

    items: list[CandidateListItem] = []
    for c in rows:
        nationality_name = None
        if c.nationality_id:
            nationality = await session.get(Nationality, c.nationality_id)
            nationality_name = nationality.name if nationality else None

        channel_name = None
        if c.source_channel_id:
            ch = await session.get(RecruitmentChannel, c.source_channel_id)
            channel_name = ch.name if ch else None

        app_count_q = await session.execute(
            select(func.count()).where(
                CandidateApplication.candidate_id == c.id,
                CandidateApplication.current_stage.not_in(["hired", "rejected", "withdrawn"]),
            )
        )
        active_apps = app_count_q.scalar_one()
        identity_strength = _identity_strength(c)

        items.append(
            CandidateListItem(
                id=c.id,
                full_name=c.full_name,
                phone_number=c.phone_number,
                personal_email=c.personal_email,
                current_position=c.current_position,
                current_company=c.current_company,
                nationality_name=nationality_name,
                source_channel_name=channel_name,
                active_applications=active_apps,
                identity_strength=identity_strength,
                identity_strength_label=IdentityStrengthLabels[identity_strength],
                created_at=c.created_at,
            )
        )

    return CandidateListPage(items=items, total=total, page=page, page_size=page_size)


async def get_candidate(session: AsyncSession, candidate_id: int) -> CandidateRead:
    c = await _get_candidate_or_404(session, candidate_id)
    return await _build_read(session, c)


async def check_candidate_duplicates(
    session: AsyncSession,
    data: CandidateDuplicateCheck,
) -> CandidateDuplicateCheckResult:
    normalized_full_name = _normalize_name(data.full_name)
    normalized_personal_email = _normalize_email(data.personal_email)
    normalized_phone_number = _normalize_digits(data.phone_number)
    normalized_id_number = _normalize_document(data.id_number)
    normalized_passport_number = _normalize_document(data.passport_number)

    filters = []
    if normalized_personal_email:
        filters.append(func.lower(func.coalesce(Candidate.personal_email, "")) == normalized_personal_email)
    if normalized_phone_number:
        filters.append(
            func.regexp_replace(func.coalesce(Candidate.phone_number, ""), r"\D", "", "g") == normalized_phone_number
        )
    if normalized_id_number:
        filters.append(
            func.upper(func.regexp_replace(func.coalesce(Candidate.id_number, ""), r"[\s.\-]", "", "g"))
            == normalized_id_number
        )
    if normalized_passport_number:
        filters.append(
            func.upper(func.regexp_replace(func.coalesce(Candidate.passport_number, ""), r"[\s.\-]", "", "g"))
            == normalized_passport_number
        )
    if normalized_full_name:
        filters.append(func.lower(func.trim(func.coalesce(Candidate.full_name, ""))) == data.full_name.strip().lower())

    if not filters:
        return CandidateDuplicateCheckResult(exact_matches=[], possible_matches=[])

    query = select(Candidate).where(Candidate.is_active == True)  # noqa: E712
    query = query.where(or_(*filters))
    if data.exclude_candidate_id:
        query = query.where(Candidate.id != data.exclude_candidate_id)

    result = await session.execute(query.order_by(Candidate.updated_at.desc(), Candidate.id.desc()).limit(20))
    rows = result.scalars().all()

    exact_matches: list[CandidateDuplicateMatch] = []
    possible_matches: list[CandidateDuplicateMatch] = []
    for candidate in rows:
        exact_reason_codes, possible_reason_codes = _candidate_duplicate_reasons(candidate, data)
        if exact_reason_codes:
            exact_matches.append(
                _build_duplicate_match(candidate, "exact", exact_reason_codes + possible_reason_codes)
            )
        elif possible_reason_codes:
            possible_matches.append(
                _build_duplicate_match(candidate, "possible", possible_reason_codes)
            )

    return CandidateDuplicateCheckResult(
        exact_matches=exact_matches,
        possible_matches=possible_matches,
    )


async def create_candidate(
    session: AsyncSession, data: CandidateCreate, created_by_id: int
) -> CandidateRead:
    payload = data.model_dump()
    if payload.get("full_name") and (not payload.get("last_name") or not payload.get("first_name")):
        last_name, first_name = _split_full_name(payload["full_name"])
        payload["last_name"] = payload.get("last_name") or last_name
        payload["first_name"] = payload.get("first_name") or first_name
    payload["nationality_id"] = await _resolve_nationality_id(
        session,
        payload.get("nationality_id"),
        payload.get("raw_nationality_text"),
    )
    c = Candidate(**payload, created_by_id=created_by_id)
    session.add(c)
    await session.flush()
    return await _build_read(session, c)


async def update_candidate(
    session: AsyncSession, candidate_id: int, data: CandidateUpdate
) -> CandidateRead:
    c = await _get_candidate_or_404(session, candidate_id)
    patch = data.model_dump(exclude_unset=True)
    next_full_name = patch.get("full_name", c.full_name)
    next_last_name = patch.get("last_name", c.last_name)
    next_first_name = patch.get("first_name", c.first_name)
    if next_full_name and (not next_last_name or not next_first_name):
        derived_last_name, derived_first_name = _split_full_name(next_full_name)
        patch["last_name"] = next_last_name or derived_last_name
        patch["first_name"] = next_first_name or derived_first_name
    if "nationality_id" in patch or "raw_nationality_text" in patch:
        patch["nationality_id"] = await _resolve_nationality_id(
            session,
            patch.get("nationality_id", c.nationality_id),
            patch.get("raw_nationality_text", c.raw_nationality_text),
        )
    for k, v in patch.items():
        setattr(c, k, v)
    c.updated_at = _utcnow()
    await session.flush()
    return await _build_read(session, c)


async def delete_candidate(session: AsyncSession, candidate_id: int) -> None:
    """Soft-delete: is_active=False (GDPR)."""
    c = await _get_candidate_or_404(session, candidate_id)
    c.is_active = False
    c.updated_at = _utcnow()
    await session.flush()


# ── Education sub-resource ────────────────────────────────────────────────────


async def add_education(
    session: AsyncSession, candidate_id: int, data: CandidateEducationCreate
) -> CandidateEducationRead:
    await _get_candidate_or_404(session, candidate_id)
    institution, major, level = await _resolve_education_refs(session, data)
    edu = CandidateEducation(
        candidate_id=candidate_id,
        institution_id=institution.id,
        institution_name=institution.name,
        major_id=major.id if major else None,
        major_name=major.name if major else None,
        education_level_id=level.id,
        graduation_year=data.graduation_year,
        diploma_type=data.diploma_type,
        is_main_education=data.is_main_education,
        note=data.note,
    )
    session.add(edu)
    await session.flush()
    return _edu_read(edu, level.name)


async def update_education(
    session: AsyncSession, candidate_id: int, edu_id: int, data: CandidateEducationCreate
) -> CandidateEducationRead:
    await _get_candidate_or_404(session, candidate_id)
    edu = await session.get(CandidateEducation, edu_id)
    if not edu or edu.candidate_id != candidate_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy học vấn")
    institution, major, level = await _resolve_education_refs(session, data)
    edu.institution_id = institution.id
    edu.institution_name = institution.name
    edu.major_id = major.id if major else None
    edu.major_name = major.name if major else None
    edu.education_level_id = level.id
    edu.graduation_year = data.graduation_year
    edu.diploma_type = data.diploma_type
    edu.is_main_education = data.is_main_education
    edu.note = data.note
    await session.flush()
    return _edu_read(edu, level.name)


async def delete_education(session: AsyncSession, candidate_id: int, edu_id: int) -> None:
    await _get_candidate_or_404(session, candidate_id)
    edu = await session.get(CandidateEducation, edu_id)
    if not edu or edu.candidate_id != candidate_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy học vấn")
    await session.delete(edu)
    await session.flush()


# ── Work experience sub-resource ──────────────────────────────────────────────


async def add_work_experience(
    session: AsyncSession, candidate_id: int, data: CandidateWorkExpCreate
) -> CandidateWorkExpRead:
    await _get_candidate_or_404(session, candidate_id)
    exp = CandidateWorkExperience(candidate_id=candidate_id, **data.model_dump())
    session.add(exp)
    await session.flush()
    return CandidateWorkExpRead(
        id=exp.id,
        candidate_id=exp.candidate_id,
        company_name=exp.company_name,
        position_name=exp.position_name,
        start_date=exp.start_date,
        end_date=exp.end_date,
        description=exp.description,
        sort_order=exp.sort_order,
    )


async def update_work_experience(
    session: AsyncSession, candidate_id: int, exp_id: int, data: CandidateWorkExpCreate
) -> CandidateWorkExpRead:
    await _get_candidate_or_404(session, candidate_id)
    exp = await session.get(CandidateWorkExperience, exp_id)
    if not exp or exp.candidate_id != candidate_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kinh nghiệm")
    for k, v in data.model_dump().items():
        setattr(exp, k, v)
    await session.flush()
    return CandidateWorkExpRead(
        id=exp.id,
        candidate_id=exp.candidate_id,
        company_name=exp.company_name,
        position_name=exp.position_name,
        start_date=exp.start_date,
        end_date=exp.end_date,
        description=exp.description,
        sort_order=exp.sort_order,
    )


async def delete_work_experience(session: AsyncSession, candidate_id: int, exp_id: int) -> None:
    await _get_candidate_or_404(session, candidate_id)
    exp = await session.get(CandidateWorkExperience, exp_id)
    if not exp or exp.candidate_id != candidate_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kinh nghiệm")
    await session.delete(exp)
    await session.flush()


# ── Skills sub-resource ───────────────────────────────────────────────────────


async def add_skill(
    session: AsyncSession, candidate_id: int, data: CandidateSkillCreate
) -> CandidateSkillRead:
    await _get_candidate_or_404(session, candidate_id)
    # Check duplicate
    existing = await session.execute(
        select(CandidateSkill).where(
            CandidateSkill.candidate_id == candidate_id,
            CandidateSkill.skill_name == data.skill_name,
        )
    )
    if existing.scalars().first():
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Kỹ năng đã tồn tại")
    sk = CandidateSkill(candidate_id=candidate_id, **data.model_dump())
    session.add(sk)
    await session.flush()
    return CandidateSkillRead(
        id=sk.id,
        candidate_id=sk.candidate_id,
        skill_name=sk.skill_name,
        proficiency_level=sk.proficiency_level,
    )


async def delete_skill(session: AsyncSession, candidate_id: int, skill_id: int) -> None:
    await _get_candidate_or_404(session, candidate_id)
    sk = await session.get(CandidateSkill, skill_id)
    if not sk or sk.candidate_id != candidate_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy kỹ năng")
    await session.delete(sk)
    await session.flush()


# ── Application ───────────────────────────────────────────────────────────────


async def apply_candidate(
    session: AsyncSession,
    candidate_id: int,
    data: ApplicationCreate,
    created_by_id: int,
) -> ApplicationRead:
    c = await _get_candidate_or_404(session, candidate_id)

    jr = await session.get(JobRequisition, data.job_requisition_id)
    if not jr:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy JR")
    if jr.status not in ("approved", "in_progress"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="JR phải ở trạng thái đã duyệt hoặc đang tuyển",
        )

    # Check unique constraint
    existing = await session.execute(
        select(CandidateApplication).where(
            CandidateApplication.candidate_id == candidate_id,
            CandidateApplication.job_requisition_id == data.job_requisition_id,
        )
    )
    if existing.scalars().first():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Ứng viên đã ứng tuyển vào JR này rồi",
        )

    app = CandidateApplication(
        candidate_id=candidate_id,
        job_requisition_id=data.job_requisition_id,
        applied_date=data.applied_date,
        source_channel_id=data.source_channel_id,
        internal_note=data.internal_note,
        created_by_id=created_by_id,
    )

    first_stage_q = await session.execute(
        select(PipelineStage)
        .where(
            PipelineStage.job_requisition_id == data.job_requisition_id,
            PipelineStage.is_active == True,  # noqa: E712
        )
        .order_by(PipelineStage.stage_order, PipelineStage.id)
        .limit(1)
    )
    first_stage = first_stage_q.scalars().first()
    if first_stage:
        app.current_stage = first_stage.stage_type

    session.add(app)

    # Transition JR to in_progress if still approved
    if jr.status == "approved":
        jr.status = "in_progress"
        jr.updated_at = _utcnow()

    await session.flush()

    return await _build_application_read(session, app)


async def list_applications(
    session: AsyncSession,
    jr_id: int,
    stage: Optional[str],
    page: int,
    page_size: int,
) -> ApplicationListPage:
    base = select(CandidateApplication).where(CandidateApplication.job_requisition_id == jr_id)
    if stage:
        base = base.where(CandidateApplication.current_stage == stage)

    total_q = await session.execute(select(func.count()).select_from(base.subquery()))
    total = total_q.scalar_one()

    rows_q = await session.execute(
        base.order_by(CandidateApplication.applied_date.desc(), CandidateApplication.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = rows_q.scalars().all()
    items = [await _build_application_read(session, r) for r in rows]

    return ApplicationListPage(items=items, total=total, page=page, page_size=page_size)


async def list_candidate_applications(
    session: AsyncSession,
    candidate_id: int,
    page: int,
    page_size: int,
) -> ApplicationListPage:
    await _get_candidate_or_404(session, candidate_id)

    base = select(CandidateApplication).where(CandidateApplication.candidate_id == candidate_id)
    total_q = await session.execute(select(func.count()).select_from(base.subquery()))
    total = total_q.scalar_one()

    rows_q = await session.execute(
        base.order_by(CandidateApplication.applied_date.desc(), CandidateApplication.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = rows_q.scalars().all()
    items = [await _build_application_read(session, r) for r in rows]

    return ApplicationListPage(items=items, total=total, page=page, page_size=page_size)


async def get_application(
    session: AsyncSession,
    application_id: int,
) -> ApplicationRead:
    app = await session.get(CandidateApplication, application_id)
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Không tìm thấy hồ sơ ứng tuyển")
    return await _build_application_read(session, app)


async def _build_application_read(
    session: AsyncSession, app: CandidateApplication
) -> ApplicationRead:
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
