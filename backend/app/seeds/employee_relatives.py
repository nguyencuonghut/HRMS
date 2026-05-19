"""Seed người thân mẫu cho một số nhân viên — chỉ dùng trên môi trường dev/test.

Idempotent: kiểm tra employee đã có người thân chưa trước khi insert.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _d(s: str) -> date:
    return date.fromisoformat(s)


# (employee_id_number, full_name, relationship_type, date_of_birth, occupation, phone_number, is_emergency_contact)
RELATIVES = [
    ("001088123456", "Trần Thị Lan",    "vo",   "1990-06-20", "Giáo viên",    "0912345678", True),
    ("001088123456", "Nguyễn Văn Bình", "cha",  "1960-02-10", "Nông dân",     None,         False),
    ("038092456789", "Lê Văn Nam",      "chong","1985-11-05", "Kỹ sư",        "0923456789", True),
    ("001085654321", "Lê Thị Mai",      "me",   "1962-07-15", "Nội trợ",      "0934567890", True),
    ("001085654321", "Lê Văn Tuấn",     "anh",  "1991-03-22", "Kinh doanh",   None,         False),
]


async def seed_sample_relatives(session: AsyncSession) -> int:
    """Seed người thân mẫu. Idempotent — bỏ qua employee đã có dữ liệu."""
    added = 0
    for employee_id_number, full_name, rel_type, dob, occupation, phone, is_emergency in RELATIVES:
        result = await session.execute(
            text("""
                INSERT INTO employee_relatives (
                    employee_id, full_name, relationship_type,
                    date_of_birth, occupation, phone_number,
                    is_emergency_contact, created_at
                )
                SELECT
                    e.id,
                    :full_name, :rel_type,
                    :dob, :occupation, :phone,
                    :is_emergency, now()
                FROM employees e
                WHERE e.id_number = :employee_id_number
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_relatives r
                      WHERE r.employee_id = e.id
                        AND r.full_name = CAST(:full_name AS varchar)
                  )
            """),
            {
                "employee_id_number": employee_id_number,
                "full_name": full_name,
                "rel_type": rel_type,
                "dob": _d(dob),
                "occupation": occupation,
                "phone": phone,
                "is_emergency": is_emergency,
            },
        )
        added += result.rowcount
    return added
