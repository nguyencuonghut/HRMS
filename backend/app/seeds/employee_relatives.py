"""Seed người thân mẫu cho một số nhân viên — chỉ dùng trên môi trường dev/test.

Idempotent: kiểm tra employee đã có người thân chưa trước khi insert.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import hash_sensitive

def _d(s: str) -> date:
    return date.fromisoformat(s)


# (
#   employee_id_number, full_name, relationship_type, date_of_birth,
#   occupation, phone_number, is_emergency_contact,
#   participates_in_health_care_insurance
# )
RELATIVES = [
    ("001088123456", "Trần Thị Lan",    "vo",    "1990-06-20", "Giáo viên",          "0912345678", True,  False),
    ("001088123456", "Nguyễn Văn Bình", "cha",   "1960-02-10", "Nông dân",           None,         False, False),
    ("038092456789", "Lê Văn Nam",      "chong", "1985-11-05", "Kỹ sư",              "0923456789", True,  False),
    ("001085654321", "Lê Thị Mai",      "me",    "1962-07-15", "Nội trợ",            "0934567890", True,  False),
    ("001085654321", "Lê Văn Tuấn",     "anh",   "1991-03-22", "Kinh doanh",         None,         False, False),
    ("079086444444", "Nguyễn Thị Hồng", "vo",    "1988-03-12", "Kế toán nội bộ",     "0908111222", True,  True),
    ("079086444444", "Tạ Gia Bảo",      "con",   "2012-09-01", "Học sinh",           None,         False, True),
    ("079086444444", "Tạ Minh Châu",    "con",   "2016-04-18", "Học sinh",           None,         False, True),
    ("079086444444", "Tạ Văn Hùng",     "cha",   "1961-07-20", "Nghỉ hưu",           None,         False, False),
    ("079086444444", "Nguyễn Thị Hạnh", "me",    "1964-11-02", "Buôn bán nhỏ",       None,         False, False),
    ("079094777777", "Lê Quốc Khánh",   "chong", "1989-05-09", "Kỹ sư hệ thống",     "0909777888", True,  True),
    ("079094777777", "Lê Gia Linh",     "con",   "2018-08-25", "Mẫu giáo",           None,         False, True),
    ("079094777777", "Phạm Thị Xuân",   "me",    "1962-01-15", "Nội trợ",            None,         False, False),
    ("079091555555", "Trần Minh Phúc",  "con",   "2010-06-30", "Học sinh",           None,         True,  False),
]


async def seed_sample_relatives(session: AsyncSession) -> int:
    """Seed người thân mẫu. Idempotent — bỏ qua employee đã có dữ liệu."""
    added = 0
    for (
        employee_id_number,
        full_name,
        rel_type,
        dob,
        occupation,
        phone,
        is_emergency,
        participates_in_health_care_insurance,
    ) in RELATIVES:
        result = await session.execute(
            text("""
                INSERT INTO employee_relatives (
                    employee_id, full_name, relationship_type,
                    date_of_birth, occupation, phone_number,
                    is_emergency_contact, participates_in_health_care_insurance, created_at
                )
                SELECT
                    e.id,
                    :full_name, :rel_type,
                    :dob, :occupation, :phone,
                    :is_emergency, :participates_in_health_care_insurance, now()
                FROM employees e
                WHERE e.id_number_hash = :employee_id_number_hash
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_relatives r
                      WHERE r.employee_id = e.id
                        AND r.full_name = CAST(:full_name AS varchar)
                  )
            """),
            {
                "employee_id_number_hash": hash_sensitive(employee_id_number),
                "full_name": full_name,
                "rel_type": rel_type,
                "dob": _d(dob),
                "occupation": occupation,
                "phone": phone,
                "is_emergency": is_emergency,
                "participates_in_health_care_insurance": participates_in_health_care_insurance,
            },
        )
        added += result.rowcount
    return added
