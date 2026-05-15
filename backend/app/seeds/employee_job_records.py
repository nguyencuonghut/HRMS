"""Seed bản ghi công việc cho 10 nhân viên mẫu.

Idempotent: kiểm tra is_current trước khi insert, bỏ qua nếu đã có.
Cũng cập nhật display_prefix cho một số phòng ban để demo display_code có prefix.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _d(s: str) -> date:
    return date.fromisoformat(s)

# Gán display_prefix cho các phòng ban chính
DEPT_PREFIXES = {
    "HC":  "HC",
    "KD":  "KD",
    "PK":  "KT",
    "KT":  "KT2",
    "DA":  "DA",
    "TM":  "TM",
    "BT":  "BT",
    "SX":  "SX",
    "MKT": "MK",
    "CL":  "CL",
}

# (employee_seq, dept_code, job_title_code, effective_from, status_after)
ASSIGNMENTS = [
    (1,  "HC",  "TP",   "2024-01-15", "official"),
    (2,  "PK",  "NV",   "2024-03-01", "official"),
    (3,  "KD",  "NVKD", "2024-06-15", "official"),
    (4,  "PK",  "NV",   "2024-09-01", "official"),
    (5,  "KD",  "NVKD", "2025-01-01", "official"),
    (6,  "HC",  "NV",   "2025-04-01", "official"),
    (7,  "KD",  "NVKD", "2025-11-01", "probation"),
    (8,  "HC",  "NV",   "2026-03-01", "probation"),
    (9,  "PK",  "NV",   "2026-04-15", "probation"),
    (10, "KD",  "NVKD", "2023-06-01", "resigned"),
]

# Bản ghi lịch sử thêm cho nhân viên 1 (demo tab lịch sử):
# Trước khi vào HC, An từng ở KD từ 2024-01-15 → 2024-06-14
HISTORY_RECORD = {
    "employee_seq": 1,
    "dept_code": "KD",
    "job_title_code": "NVKD",
    "effective_from": "2024-01-15",
    "effective_to": "2024-06-14",
}


async def seed_sample_job_records(session: AsyncSession) -> int:
    """Seed job records. Idempotent — bỏ qua employee đã có bản ghi is_current."""
    added = 0

    # Cập nhật display_prefix cho phòng ban
    for code, prefix in DEPT_PREFIXES.items():
        await session.execute(
            text("UPDATE departments SET display_prefix = :prefix WHERE code = :code AND display_prefix IS NULL"),
            {"code": code, "prefix": prefix},
        )

    # Thêm bản ghi lịch sử cho NV 1 (không phải is_current)
    await session.execute(
        text("""
            INSERT INTO employee_job_records (
                employee_id, department_id, job_title_id,
                effective_from, effective_to, is_current, created_at
            )
            SELECT
                e.id,
                (SELECT id FROM departments WHERE code = :dept_code),
                (SELECT id FROM job_titles WHERE code = :title_code),
                :effective_from, :effective_to, false, now()
            FROM employees e
            WHERE e.employee_seq = :employee_seq
              AND NOT EXISTS (
                  SELECT 1 FROM employee_job_records r
                  WHERE r.employee_id = e.id
                    AND r.is_current = false
                    AND r.effective_from = :effective_from
              )
        """),
        {
            "employee_seq": HISTORY_RECORD["employee_seq"],
            "dept_code": HISTORY_RECORD["dept_code"],
            "title_code": HISTORY_RECORD["job_title_code"],
            "effective_from": _d(HISTORY_RECORD["effective_from"]),
            "effective_to": _d(HISTORY_RECORD["effective_to"]),
        },
    )

    # Thêm bản ghi is_current cho từng nhân viên
    for emp_seq, dept_code, title_code, effective_from, _ in ASSIGNMENTS:
        result = await session.execute(
            text("""
                INSERT INTO employee_job_records (
                    employee_id, department_id, job_title_id,
                    effective_from, is_current, created_at
                )
                SELECT
                    e.id,
                    (SELECT id FROM departments WHERE code = :dept_code),
                    (SELECT id FROM job_titles WHERE code = :title_code),
                    :effective_from, true, now()
                FROM employees e
                WHERE e.employee_seq = :employee_seq
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_job_records r
                      WHERE r.employee_id = e.id AND r.is_current = true
                  )
            """),
            {
                "employee_seq": emp_seq,
                "dept_code": dept_code,
                "title_code": title_code,
                "effective_from": _d(effective_from),
            },
        )
        added += result.rowcount

    return added
