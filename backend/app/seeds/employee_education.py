"""Seed học vấn, kinh nghiệm, kỹ năng, chứng chỉ, ngoại ngữ mẫu.

Idempotent: kiểm tra employee đã có dữ liệu ở từng bảng trước khi insert.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import hash_sensitive

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
    # Tra cứu institution/major/level theo MÃ (code) thay vì id cứng — id tự tăng
    # có thể lệch giữa các môi trường tuỳ lịch sử insert/delete của danh mục.
    # (employee_id_number, institution_code, institution_name, major_code, major_name,
    #  level_code, grad_year, diploma_type, is_main)
    EDUCATIONS = [
        # seq=1: Học viện Nông nghiệp VN, Thú y, Đại học 2012 — bằng chính
        ("001088123456", "VNUA", None, "veterinary_medicine", None, "bachelor", 2012, "chính quy", True),
        # seq=3: ĐH Nông Lâm HCM, Kinh doanh nông nghiệp (free text), ĐH 2015
        ("001085654321", "NLU_HCMC", None, None, "Kinh doanh nông nghiệp", "bachelor", 2015, "chính quy", True),
    ]
    for employee_id_number, inst_code, inst_name, major_code, major_name, level_code, grad_year, diploma, is_main in EDUCATIONS:
        result = await session.execute(
            text("""
                INSERT INTO employee_education_histories (
                    employee_id, institution_id, institution_name,
                    major_id, major_name, education_level_id,
                    graduation_year, diploma_type, is_main_education, created_at
                )
                SELECT
                    e.id,
                    (SELECT id FROM educational_institutions WHERE code = CAST(:inst_code AS varchar)),
                    :inst_name,
                    (SELECT id FROM education_majors WHERE code = CAST(:major_code AS varchar)),
                    :major_name,
                    (SELECT id FROM education_levels WHERE code = :level_code),
                    :grad_year, :diploma, :is_main, now()
                FROM employees e
                WHERE e.id_number_hash = :employee_id_number_hash
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_education_histories h
                      WHERE h.employee_id = e.id
                        AND (
                            (CAST(:inst_code AS varchar) IS NOT NULL AND h.institution_id = (SELECT id FROM educational_institutions WHERE code = CAST(:inst_code AS varchar)))
                            OR (CAST(:inst_name AS varchar) IS NOT NULL AND h.institution_name = CAST(:inst_name AS varchar))
                        )
                  )
            """),
            {
                "employee_id_number_hash": hash_sensitive(employee_id_number),
                "inst_code": inst_code,
                "inst_name": inst_name,
                "major_code": major_code,
                "major_name": major_name,
                "level_code": level_code,
                "grad_year": grad_year,
                "diploma": diploma,
                "is_main": is_main,
            },
        )
        counts["education_histories"] += result.rowcount

    # ── 2. Kinh nghiệm làm việc ────────────────────────────────────────────────
    # (employee_id_number, company_name, position_name, start_date, end_date)
    EXPERIENCES = [
        ("001088123456", "Công ty CP Chăn nuôi ABC", "Kỹ thuật viên thú y", "2010-06-01", "2011-12-31"),
        ("001085654321", "Công ty TNHH XYZ",        "Nhân viên kinh doanh", "2015-08-01", "2018-05-31"),
    ]
    for employee_id_number, company, position, start, end in EXPERIENCES:
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
                WHERE e.id_number_hash = :employee_id_number_hash
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_work_experiences w
                      WHERE w.employee_id = e.id
                        AND w.company_name = CAST(:company AS varchar)
                  )
            """),
            {
                "employee_id_number_hash": hash_sensitive(employee_id_number),
                "company": company,
                "position": position,
                "start": _d(start),
                "end": _d(end),
            },
        )
        counts["work_experiences"] += result.rowcount

    # ── 3. Kỹ năng ────────────────────────────────────────────────────────────
    # (employee_id_number, skill_code, proficiency_level)
    SKILLS = [
        ("001088123456", "qa_qc", "expert"),               # QA/QC — Thành thạo
        ("001085654321", "import_export_ops", "advanced"),  # Nghiệp vụ xuất nhập khẩu — Khá
    ]
    for employee_id_number, skill_code, level in SKILLS:
        result = await session.execute(
            text("""
                INSERT INTO employee_skills (
                    employee_id, skill_id, proficiency_level, created_at
                )
                SELECT e.id, sk.id, :level, now()
                FROM employees e, skills sk
                WHERE e.id_number_hash = :employee_id_number_hash
                  AND sk.code = :skill_code
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_skills s
                      WHERE s.employee_id = e.id AND s.skill_id = sk.id
                  )
            """),
            {"employee_id_number_hash": hash_sensitive(employee_id_number), "skill_code": skill_code, "level": level},
        )
        counts["skills"] += result.rowcount

    # ── 4. Chứng chỉ ──────────────────────────────────────────────────────────
    # (employee_id_number, certificate_code, issued_date, expires_on)
    CERTIFICATES = [
        ("001088123456", "HACCP", "2024-01-15", "2027-01-15"),
        ("001085654321", "OSH", "2023-06-01", None),  # An toàn vệ sinh lao động
    ]
    for employee_id_number, cert_code, issued, expires in CERTIFICATES:
        result = await session.execute(
            text("""
                INSERT INTO employee_certificates (
                    employee_id, certificate_id, issued_date, expires_on, created_at
                )
                SELECT e.id, c.id, :issued, :expires, now()
                FROM employees e, certificates c
                WHERE e.id_number_hash = :employee_id_number_hash
                  AND c.code = :cert_code
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_certificates ec
                      WHERE ec.employee_id = e.id AND ec.certificate_id = c.id
                  )
            """),
            {
                "employee_id_number_hash": hash_sensitive(employee_id_number),
                "cert_code": cert_code,
                "issued": _d(issued),
                "expires": _d(expires) if expires else None,
            },
        )
        counts["certificates"] += result.rowcount

    # ── 5. Ngoại ngữ ──────────────────────────────────────────────────────────
    # (employee_id_number, language_name, proficiency_level)
    LANGUAGES = [
        ("001088123456", "Tiếng Anh",  "B2"),
        ("001085654321", "Tiếng Anh",  "B1"),
        ("001085654321", "Tiếng Trung", "A2"),
    ]
    for employee_id_number, lang, level in LANGUAGES:
        result = await session.execute(
            text("""
                INSERT INTO employee_languages (
                    employee_id, language_name, proficiency_level, created_at
                )
                SELECT e.id, :lang, :level, now()
                FROM employees e
                WHERE e.id_number_hash = :employee_id_number_hash
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_languages l
                      WHERE l.employee_id = e.id
                        AND l.language_name = CAST(:lang AS varchar)
                  )
            """),
            {"employee_id_number_hash": hash_sensitive(employee_id_number), "lang": lang, "level": level},
        )
        counts["languages"] += result.rowcount

    return counts
