"""Seed bản ghi công việc cho nhân viên mẫu.

Idempotent: kiểm tra is_current trước khi insert, bỏ qua nếu đã có.
Cũng cập nhật display_prefix cho một số phòng ban để demo display_code có prefix.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import hash_sensitive

def _d(s: str) -> date:
    return date.fromisoformat(s)

# Gán display_prefix cho các phòng ban chính
DEPT_PREFIXES = {
    "HC":  "HC",
    "KD":  "KD",
    "KS":  "KS",
    "KSNB": "KSNB",
    "IT":  "IT",
    "PK":  "KT",
    "KT":  "KT2",
    "DA":  "DA",
    "TM":  "TM",
    "BT":  "BT",
    "SX":  "SX",
    "MKT": "MK",
    "CL":  "CL",
}

ASSIGNMENTS = [
    {
        "employee_id_number": "001088123456",
        "dept_code": "HC",
        "job_title_code": "TP",
        "job_position_code": None,
        "effective_from": "2024-01-15",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2024-01-15",
    },
    {
        "employee_id_number": "038092456789",
        "dept_code": "PK",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2024-03-01",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2024-03-01",
    },
    {
        "employee_id_number": "001085654321",
        "dept_code": "KD",
        "job_title_code": "NVKD",
        "job_position_code": None,
        "effective_from": "2024-06-15",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2024-06-15",
    },
    {
        "employee_id_number": "086095789012",
        "dept_code": "PK",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2024-09-01",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2024-09-01",
    },
    {
        "employee_id_number": "020090345678",
        "dept_code": "KD",
        "job_title_code": "NVKD",
        "job_position_code": None,
        "effective_from": "2025-01-01",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2025-01-01",
    },
    {
        "employee_id_number": "079094567890",
        "dept_code": "HC",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2025-04-01",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2025-04-01",
    },
    {
        "employee_id_number": "036099678901",
        "dept_code": "KD",
        "job_title_code": "NVKD",
        "job_position_code": None,
        "effective_from": "2025-11-01",
        "probation_start_date": "2025-11-01",
        "probation_end_date": "2025-12-31",
        "official_date": None,
    },
    {
        "employee_id_number": "001201789012",
        "dept_code": "HC",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2026-03-01",
        "probation_start_date": "2026-03-01",
        "probation_end_date": "2026-04-30",
        "official_date": None,
    },
    {
        "employee_id_number": "051098890123",
        "dept_code": "PK",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2026-04-15",
        "probation_start_date": "2026-04-15",
        "probation_end_date": "2026-06-14",
        "official_date": None,
    },
    {
        "employee_id_number": "025087901234",
        "dept_code": "KD",
        "job_title_code": "NVKD",
        "job_position_code": None,
        "effective_from": "2023-06-01",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2023-06-01",
    },
    {
        "employee_id_number": "079064111111",
        "dept_code": "HC",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2012-05-10",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2012-05-10",
    },
    {
        "employee_id_number": "019068222222",
        "dept_code": "PK",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2014-08-01",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2014-08-01",
    },
    {
        "employee_id_number": "079067333333",
        "dept_code": "KD",
        "job_title_code": "NVKD",
        "job_position_code": None,
        "effective_from": "2010-03-15",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2010-03-15",
    },
    {
        "employee_id_number": "079086444444",
        "dept_code": "KS",
        "job_title_code": "TP",
        "job_position_code": "TP_KSNB",
        "effective_from": "2022-01-10",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2022-01-10",
    },
    {
        "employee_id_number": "079091555555",
        "dept_code": "KSNB",
        "job_title_code": "TBP",
        "job_position_code": "TN_KSNB",
        "effective_from": "2022-03-01",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2022-03-01",
    },
    {
        "employee_id_number": "079093666666",
        "dept_code": "KSNB",
        "job_title_code": "NV",
        "job_position_code": "NV_KSNB",
        "effective_from": "2022-06-15",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2022-06-15",
    },
    {
        "employee_id_number": "079094777777",
        "dept_code": "IT",
        "job_title_code": "NVKT",
        "job_position_code": "CV_IT",
        "effective_from": "2023-02-06",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2023-02-06",
    },
    {
        "employee_id_number": "079096888888",
        "dept_code": "IT",
        "job_title_code": "NV",
        "job_position_code": "NV_IT",
        "effective_from": "2023-05-08",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2023-05-08",
    },
    {
        "employee_id_number": "079096999991",
        "dept_code": "HC",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2026-01-08",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2026-01-08",
    },
    {
        "employee_id_number": "079097999992",
        "dept_code": "PK",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2026-03-05",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2026-03-05",
    },
    {
        "employee_id_number": "079094999993",
        "dept_code": "KD",
        "job_title_code": "NVKD",
        "job_position_code": None,
        "effective_from": "2026-03-18",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2026-03-18",
    },
    {
        "employee_id_number": "079098999994",
        "dept_code": "PK",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2026-06-03",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2026-06-03",
    },
    {
        "employee_id_number": "079095999995",
        "dept_code": "KD",
        "job_title_code": "NVKD",
        "job_position_code": None,
        "effective_from": "2026-06-12",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2026-06-12",
    },
    {
        "employee_id_number": "079099999996",
        "dept_code": "HC",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2026-09-02",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2026-09-02",
    },
    {
        "employee_id_number": "079092999997",
        "dept_code": "KD",
        "job_title_code": "NVKD",
        "job_position_code": None,
        "effective_from": "2024-07-15",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2024-07-15",
    },
    {
        "employee_id_number": "079090999998",
        "dept_code": "HC",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2023-03-01",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2023-03-01",
    },
    {
        "employee_id_number": "079096999999",
        "dept_code": "PK",
        "job_title_code": "NV",
        "job_position_code": None,
        "effective_from": "2024-11-20",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2024-11-20",
    },
    {
        "employee_id_number": "079089999900",
        "dept_code": "KD",
        "job_title_code": "NVKD",
        "job_position_code": None,
        "effective_from": "2022-06-10",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2022-06-10",
    },
    {
        "employee_id_number": "079097999901",
        "dept_code": "IT",
        "job_title_code": "NV",
        "job_position_code": "NV_IT",
        "effective_from": "2026-11-11",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2026-11-11",
    },
    {
        "employee_id_number": "079091999902",
        "dept_code": "IT",
        "job_title_code": "NVKT",
        "job_position_code": "CV_IT",
        "effective_from": "2024-01-22",
        "probation_start_date": None,
        "probation_end_date": None,
        "official_date": "2024-01-22",
    },
]

# Bản ghi lịch sử thêm cho nhân viên 1 (demo tab lịch sử):
# Trước khi vào HC, An từng ở KD từ 2024-01-15 → 2024-06-14
HISTORY_RECORD = {
    "employee_id_number": "001088123456",
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
            WHERE e.id_number_hash = :employee_id_number_hash
              AND NOT EXISTS (
                  SELECT 1 FROM employee_job_records r
                  WHERE r.employee_id = e.id
                    AND r.is_current = false
                    AND r.effective_from = :effective_from
              )
        """),
        {
            "employee_id_number_hash": hash_sensitive(HISTORY_RECORD["employee_id_number"]),
            "dept_code": HISTORY_RECORD["dept_code"],
            "title_code": HISTORY_RECORD["job_title_code"],
            "effective_from": _d(HISTORY_RECORD["effective_from"]),
            "effective_to": _d(HISTORY_RECORD["effective_to"]),
        },
    )

    # Thêm bản ghi is_current cho từng nhân viên
    for assignment in ASSIGNMENTS:
        result = await session.execute(
            text("""
                INSERT INTO employee_job_records (
                    employee_id, department_id, job_title_id, job_position_id,
                    effective_from, probation_start_date, probation_end_date, official_date,
                    is_current, created_at
                )
                SELECT
                    e.id,
                    (SELECT id FROM departments WHERE code = :dept_code),
                    (SELECT id FROM job_titles WHERE code = :title_code),
                    (SELECT id FROM job_positions WHERE code = :job_position_code),
                    :effective_from, :probation_start_date, :probation_end_date, :official_date,
                    true, now()
                FROM employees e
                WHERE e.id_number_hash = :employee_id_number_hash
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_job_records r
                      WHERE r.employee_id = e.id AND r.is_current = true
                  )
            """),
            {
                "employee_id_number_hash": hash_sensitive(assignment["employee_id_number"]),
                "dept_code": assignment["dept_code"],
                "title_code": assignment["job_title_code"],
                "job_position_code": assignment["job_position_code"],
                "effective_from": _d(assignment["effective_from"]),
                "probation_start_date": _d(assignment["probation_start_date"]) if assignment["probation_start_date"] else None,
                "probation_end_date": _d(assignment["probation_end_date"]) if assignment["probation_end_date"] else None,
                "official_date": _d(assignment["official_date"]) if assignment["official_date"] else None,
            },
        )
        added += result.rowcount

    return added
