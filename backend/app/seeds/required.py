"""
Dữ liệu bắt buộc — chạy trên mọi môi trường (dev/staging/prod).

Nội dung:
  - Mức lương tối thiểu vùng theo Nghị định 293/2025/NĐ-CP (hiệu lực 01/01/2026)
  - Vùng BHXH mặc định của công ty (Vùng III — có thể sửa trong DB sau)

Seeder này idempotent: chạy nhiều lần không sinh dữ liệu trùng.
"""

import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def seed_minimum_wages(session: AsyncSession) -> int:
    """Seed mức lương tối thiểu vùng theo NĐ 293/2025/NĐ-CP.

    Returns số dòng được thêm mới (0 nếu đã tồn tại).
    """
    wages = [
        {
            "decree_number": "293/2025/NĐ-CP",
            "region": 1,
            "amount": 5_310_000,
            "effective_from": datetime.date(2026, 1, 1),
            "effective_to": None,
            "note": "Vùng I — HN (quận/huyện nội thành), TP.HCM, Đồng Nai, Bình Dương, Vũng Tàu...",
        },
        {
            "decree_number": "293/2025/NĐ-CP",
            "region": 2,
            "amount": 4_730_000,
            "effective_from": datetime.date(2026, 1, 1),
            "effective_to": None,
            "note": "Vùng II — các tỉnh/TP loại II còn lại",
        },
        {
            "decree_number": "293/2025/NĐ-CP",
            "region": 3,
            "amount": 4_140_000,
            "effective_from": datetime.date(2026, 1, 1),
            "effective_to": None,
            "note": "Vùng III — phần còn lại của các tỉnh có Vùng I/II và các tỉnh khác",
        },
        {
            "decree_number": "293/2025/NĐ-CP",
            "region": 4,
            "amount": 3_700_000,
            "effective_from": datetime.date(2026, 1, 1),
            "effective_to": None,
            "note": "Vùng IV — vùng sâu, vùng xa, miền núi, hải đảo",
        },
    ]

    inserted = 0
    for w in wages:
        result = await session.execute(
            text("""
                INSERT INTO regional_minimum_wages
                    (decree_number, region, amount, effective_from, effective_to, note)
                VALUES
                    (:decree_number, :region, :amount, :effective_from, :effective_to, :note)
                ON CONFLICT DO NOTHING
            """),
            w,
        )
        inserted += result.rowcount

    return inserted


async def seed_company_region(session: AsyncSession, region: int = 3) -> int:
    """Seed vùng BHXH của công ty. Mặc định Vùng III.

    Returns 1 nếu thêm mới, 0 nếu đã có dữ liệu.
    """
    existing = await session.execute(
        text("SELECT COUNT(*) FROM company_bhxh_region WHERE effective_to IS NULL")
    )
    if existing.scalar() > 0:
        return 0

    region_names = {1: "Vùng I", 2: "Vùng II", 3: "Vùng III", 4: "Vùng IV"}
    await session.execute(
        text("""
            INSERT INTO company_bhxh_region (region, effective_from, effective_to, note)
            VALUES (:region, :effective_from, NULL, :note)
        """),
        {
            "region": region,
            "effective_from": datetime.date(2026, 1, 1),
            "note": f"{region_names[region]} — vùng BHXH mặc định, cập nhật nếu công ty chuyển địa điểm",
        },
    )
    return 1


async def run(session: AsyncSession) -> None:
    wages_added = await seed_minimum_wages(session)
    region_added = await seed_company_region(session)
    await session.commit()

    print(f"  [required] Mức lương tối thiểu vùng: +{wages_added} dòng")
    print(f"  [required] Vùng BHXH công ty:         +{region_added} dòng")
