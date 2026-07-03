from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.seeds import document_checklist_types as checklist_seed


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _rows(sql: str):
    async with _make_session()() as session:
        return (await session.execute(text(sql))).all()


async def test_required_document_checklist_seed_reconciles_active_catalog():
    async with _make_session()() as session:
        stats = await checklist_seed.seed_required_document_checklist_types(session)
        await session.commit()

    assert set(stats.keys()) == {"inserted", "updated", "deactivated", "backfilled"}

    rows = await _rows(
        """
        SELECT code, name, is_required, has_expiry, applies_to, sort_order, is_active
        FROM document_checklist_types
        ORDER BY sort_order, code
        """
    )
    actual = [tuple(row) for row in rows]
    expected_active = [
        ("so_yeu_ly_lich", "Sơ yếu lý lịch", True, False, "all", 1, True),
        ("cccd", "CCCD", True, False, "all", 2, True),
        ("suc_khoe", "Giấy khám sức khỏe", True, True, "all", 3, True),
        ("giay_khai_sinh", "Giấy khai sinh", True, False, "all", 4, True),
        ("ho_khau", "Xác nhận cư trú", True, False, "all", 5, True),
        ("don_xin_viec", "Đơn xin việc", True, False, "all", 6, True),
        ("bang_cap", "Bằng cấp", True, False, "all", 7, True),
        ("ly_lich_tu_phap", "Giấy xác nhận dân sự", True, True, "all", 8, True),
        ("cam_ket_bao_mat_thong_tin", "Cam kết bảo mật thông tin", True, False, "all", 9, True),
    ]
    active_rows = [row for row in actual if row[-1] is True]
    assert active_rows == expected_active

    expected_active_codes = {row[0] for row in expected_active}
    unexpected_active_codes = {row[0] for row in actual if row[-1] is True and row[0] not in expected_active_codes}
    assert unexpected_active_codes == set()

    legacy_codes = {"mst", "tk_ngan_hang", "anh_the", "so_bhxh", "giay_phep_ld"}
    legacy_rows = [row for row in actual if row[0] in legacy_codes]
    assert all(row[-1] is False for row in legacy_rows)


async def test_required_document_checklist_seed_backfills_existing_employees():
    rows = await _rows(
        """
        SELECT COUNT(*)
        FROM employees e
        CROSS JOIN document_checklist_types d
        LEFT JOIN employee_document_checklists c
          ON c.employee_id = e.id
         AND c.document_type_id = d.id
        WHERE d.is_active = TRUE
          AND c.id IS NULL
        """
    )
    assert rows[0][0] == 0
