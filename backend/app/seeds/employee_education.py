"""Seed học vấn, kinh nghiệm, kỹ năng, chứng chỉ, ngoại ngữ mẫu.

Idempotent: kiểm tra employee đã có dữ liệu ở từng bảng trước khi insert.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _d(s: str) -> date:
    return date.fromisoformat(s)


async def seed_sample_education(session: AsyncSession) -> dict:
    """Seed toàn bộ dữ liệu học vấn mẫu. Trả về dict đếm số dòng inserted."""
    counts = {
        "education_histories": 0,
        "work_experiences": 0,
        "skills": 0,
        "certificates": 0,
        "languages": 0,
    }

    # ── 1. Học vấn ────────────────────────────────────────────────────────────
    # (emp_seq, institution_id, institution_name, major_id, major_name,
    #  level_id, grad_year, diploma_type, is_main)
    EDUCATIONS = [
        # seq=1: Học viện Nông nghiệp VN, Thú y, Đại học 2012 — bằng chính
        (1, 1, None, 2, None, 6, 2012, "chính quy", True),
        # seq=3: ĐH Nông Lâm HCM, Kinh doanh nông nghiệp (free text), ĐH 2015
        (3, 2, None, None, "Kinh doanh nông nghiệp", 6, 2015, "chính quy", True),
    ]
    for emp_seq, inst_id, inst_name, major_id, major_name, level_id, grad_year, diploma, is_main in EDUCATIONS:
        result = await session.execute(
            text("""
                INSERT INTO employee_education_histories (
                    employee_id, institution_id, institution_name,
                    major_id, major_name, education_level_id,
                    graduation_year, diploma_type, is_main_education, created_at
                )
                SELECT
                    e.id,
                    :inst_id, :inst_name,
                    :major_id, :major_name, :level_id,
                    :grad_year, :diploma, :is_main, now()
                FROM employees e
                WHERE e.employee_seq = :emp_seq
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_education_histories h
                      WHERE h.employee_id = e.id
                        AND (
                            (CAST(:inst_id AS integer) IS NOT NULL AND h.institution_id = CAST(:inst_id AS integer))
                            OR (CAST(:inst_name AS varchar) IS NOT NULL AND h.institution_name = CAST(:inst_name AS varchar))
                        )
                  )
            """),
            {
                "emp_seq": emp_seq,
                "inst_id": inst_id,
                "inst_name": inst_name,
                "major_id": major_id,
                "major_name": major_name,
                "level_id": level_id,
                "grad_year": grad_year,
                "diploma": diploma,
                "is_main": is_main,
            },
        )
        counts["education_histories"] += result.rowcount

    # ── 2. Kinh nghiệm làm việc ────────────────────────────────────────────────
    # (emp_seq, company_name, position_name, start_date, end_date)
    EXPERIENCES = [
        (1, "Công ty CP Chăn nuôi ABC", "Kỹ thuật viên thú y", "2010-06-01", "2011-12-31"),
        (3, "Công ty TNHH XYZ",        "Nhân viên kinh doanh", "2015-08-01", "2018-05-31"),
    ]
    for emp_seq, company, position, start, end in EXPERIENCES:
        result = await session.execute(
            text("""
                INSERT INTO employee_work_experiences (
                    employee_id, company_name, position_name,
                    start_date, end_date, created_at
                )
                SELECT
                    e.id,
                    :company, :position,
                    :start, :end, now()
                FROM employees e
                WHERE e.employee_seq = :emp_seq
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_work_experiences w
                      WHERE w.employee_id = e.id
                        AND w.company_name = CAST(:company AS varchar)
                  )
            """),
            {
                "emp_seq": emp_seq,
                "company": company,
                "position": position,
                "start": _d(start),
                "end": _d(end),
            },
        )
        counts["work_experiences"] += result.rowcount

    # ── 3. Kỹ năng ────────────────────────────────────────────────────────────
    # (emp_seq, skill_id, proficiency_level)
    SKILLS = [
        (1, 4, "expert"),    # QA/QC — Thành thạo
        (3, 8, "advanced"),  # Nghiệp vụ xuất nhập khẩu — Khá
    ]
    for emp_seq, skill_id, level in SKILLS:
        result = await session.execute(
            text("""
                INSERT INTO employee_skills (
                    employee_id, skill_id, proficiency_level, created_at
                )
                SELECT e.id, :skill_id, :level, now()
                FROM employees e
                WHERE e.employee_seq = :emp_seq
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_skills s
                      WHERE s.employee_id = e.id AND s.skill_id = :skill_id
                  )
            """),
            {"emp_seq": emp_seq, "skill_id": skill_id, "level": level},
        )
        counts["skills"] += result.rowcount

    # ── 4. Chứng chỉ ──────────────────────────────────────────────────────────
    # (emp_seq, certificate_id, issued_date, expires_on)
    CERTIFICATES = [
        (1, 2, "2024-01-15", "2027-01-15"),  # HACCP
        (3, 1, "2023-06-01", None),          # An toàn vệ sinh lao động
    ]
    for emp_seq, cert_id, issued, expires in CERTIFICATES:
        result = await session.execute(
            text("""
                INSERT INTO employee_certificates (
                    employee_id, certificate_id, issued_date, expires_on, created_at
                )
                SELECT e.id, :cert_id, :issued, :expires, now()
                FROM employees e
                WHERE e.employee_seq = :emp_seq
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_certificates c
                      WHERE c.employee_id = e.id AND c.certificate_id = :cert_id
                  )
            """),
            {
                "emp_seq": emp_seq,
                "cert_id": cert_id,
                "issued": _d(issued),
                "expires": _d(expires) if expires else None,
            },
        )
        counts["certificates"] += result.rowcount

    # ── 5. Ngoại ngữ ──────────────────────────────────────────────────────────
    # (emp_seq, language_name, proficiency_level)
    LANGUAGES = [
        (1, "Tiếng Anh",  "B2"),
        (3, "Tiếng Anh",  "B1"),
        (3, "Tiếng Trung", "A2"),
    ]
    for emp_seq, lang, level in LANGUAGES:
        result = await session.execute(
            text("""
                INSERT INTO employee_languages (
                    employee_id, language_name, proficiency_level, created_at
                )
                SELECT e.id, :lang, :level, now()
                FROM employees e
                WHERE e.employee_seq = :emp_seq
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_languages l
                      WHERE l.employee_id = e.id
                        AND l.language_name = CAST(:lang AS varchar)
                  )
            """),
            {"emp_seq": emp_seq, "lang": lang, "level": level},
        )
        counts["languages"] += result.rowcount

    return counts
