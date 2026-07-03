"""Seed tài sản cấp phát mẫu cho một số nhân viên — chỉ dùng trên môi trường dev/test.

Idempotent: kiểm tra employee đã có tài sản tương tự chưa trước khi insert.
"""

from datetime import date
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import hash_sensitive


def _d(s: str) -> date:
    return date.fromisoformat(s)


ASSETS = [
    # id_number, asset_name, asset_type, handover_date, return_date, status, note
    ("001088123456", "Laptop Dell Latitude 5420", "laptop", "2024-01-15", None, "allocated", "Cấp mới nguyên seal"),
    ("001088123456", "Sim Viettel 0988888888", "phone_sim", "2024-01-15", None, "allocated", "Sim 4G doanh nghiệp"),
    ("038092456789", "PC Văn phòng HP EliteDesk", "pc", "2023-08-10", "2024-06-01", "returned", "Đã thu hồi khi chuyển bộ phận"),
    ("038092456789", "Laptop Macbook Pro 14", "laptop", "2024-06-01", None, "allocated", "Cấp thay thế PC"),
    ("001085654321", "Sim Mobifone 0909999999", "phone_sim", "2023-05-20", None, "allocated", "Sim hotline phòng tuyển dụng"),
    ("079086444444", "Laptop ThinkPad T14 Gen 2", "laptop", "2024-03-01", None, "allocated", "Cấp kèm sạc type-C"),
]


async def seed_sample_assets(session: AsyncSession) -> int:
    """Seed tài sản cấp phát mẫu."""
    added = 0
    for (
        employee_id_number,
        asset_name,
        asset_type,
        handover_date,
        return_date,
        status,
        note,
    ) in ASSETS:
        result = await session.execute(
            text("""
                INSERT INTO employee_assets (
                    employee_id, asset_name, asset_type,
                    handover_date, return_date, status, note, created_at
                )
                SELECT
                    e.id,
                    :asset_name, :asset_type,
                    :handover_date, :return_date, :status, :note, now()
                FROM employees e
                WHERE e.id_number_hash = :employee_id_number_hash
                  AND NOT EXISTS (
                      SELECT 1 FROM employee_assets a
                      WHERE a.employee_id = e.id
                        AND a.asset_name = CAST(:asset_name AS varchar)
                  )
            """),
            {
                "employee_id_number_hash": hash_sensitive(employee_id_number),
                "asset_name": asset_name,
                "asset_type": asset_type,
                "handover_date": _d(handover_date),
                "return_date": _d(return_date) if return_date else None,
                "status": status,
                "note": note,
            },
        )
        added += result.rowcount
    return added
