"""Danh mục checklist hồ sơ pháp lý bắt buộc cho module nhân viên."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


DEFAULT_DOCUMENT_CHECKLIST_TYPES = [
    {
        "code": "so_yeu_ly_lich",
        "name": "Sơ yếu lý lịch",
        "description": None,
        "is_required": True,
        "has_expiry": False,
        "applies_to": "all",
        "sort_order": 1,
    },
    {
        "code": "cccd",
        "name": "CCCD",
        "description": None,
        "is_required": True,
        "has_expiry": False,
        "applies_to": "all",
        "sort_order": 2,
    },
    {
        "code": "suc_khoe",
        "name": "Giấy khám sức khỏe",
        "description": None,
        "is_required": True,
        "has_expiry": True,
        "applies_to": "all",
        "sort_order": 3,
    },
    {
        "code": "giay_khai_sinh",
        "name": "Giấy khai sinh",
        "description": None,
        "is_required": True,
        "has_expiry": False,
        "applies_to": "all",
        "sort_order": 4,
    },
    {
        "code": "ho_khau",
        "name": "Xác nhận cư trú",
        "description": None,
        "is_required": True,
        "has_expiry": False,
        "applies_to": "all",
        "sort_order": 5,
    },
    {
        "code": "don_xin_viec",
        "name": "Đơn xin việc",
        "description": None,
        "is_required": True,
        "has_expiry": False,
        "applies_to": "all",
        "sort_order": 6,
    },
    {
        "code": "bang_cap",
        "name": "Bằng cấp",
        "description": None,
        "is_required": True,
        "has_expiry": False,
        "applies_to": "all",
        "sort_order": 7,
    },
    {
        "code": "ly_lich_tu_phap",
        "name": "Giấy xác nhận dân sự",
        "description": None,
        "is_required": True,
        "has_expiry": True,
        "applies_to": "all",
        "sort_order": 8,
    },
    {
        "code": "cam_ket_bao_mat_thong_tin",
        "name": "Cam kết bảo mật thông tin",
        "description": "Cam kết bảo mật thông tin, tài liệu và dữ liệu nội bộ của công ty",
        "is_required": True,
        "has_expiry": False,
        "applies_to": "all",
        "sort_order": 9,
    },
]


async def seed_required_document_checklist_types(session: AsyncSession) -> dict[str, int]:
    inserted = 0
    updated = 0

    now = _utcnow()

    for item in DEFAULT_DOCUMENT_CHECKLIST_TYPES:
        exists = (
            await session.execute(
                text(
                    """
                    SELECT id, name, description, is_required, has_expiry, applies_to, sort_order, is_active
                    FROM document_checklist_types
                    WHERE code = :code
                    """
                ),
                {"code": item["code"]},
            )
        ).mappings().first()

        if exists is None:
            result = await session.execute(
                text(
                    """
                    INSERT INTO document_checklist_types
                        (code, name, description, is_required, has_expiry, applies_to, sort_order, is_active)
                    VALUES
                        (:code, :name, :description, :is_required, :has_expiry, :applies_to, :sort_order, TRUE)
                    """
                ),
                item,
            )
            inserted += result.rowcount
            continue

        if (
            exists["name"] != item["name"]
            or exists["description"] != item["description"]
            or exists["is_required"] != item["is_required"]
            or exists["has_expiry"] != item["has_expiry"]
            or exists["applies_to"] != item["applies_to"]
            or exists["sort_order"] != item["sort_order"]
            or exists["is_active"] is not True
        ):
            result = await session.execute(
                text(
                    """
                    UPDATE document_checklist_types
                    SET
                        name = :name,
                        description = :description,
                        is_required = :is_required,
                        has_expiry = :has_expiry,
                        applies_to = :applies_to,
                        sort_order = :sort_order,
                        is_active = TRUE
                    WHERE code = :code
                    """
                ),
                item,
            )
            updated += result.rowcount

    active_code_params = {
        f"code_{index}": item["code"]
        for index, item in enumerate(DEFAULT_DOCUMENT_CHECKLIST_TYPES)
    }
    placeholders = ", ".join(f":{key}" for key in active_code_params)
    deactivated = (
        await session.execute(
            text(
                f"""
                UPDATE document_checklist_types
                SET is_active = FALSE
                WHERE code NOT IN ({placeholders}) AND is_active = TRUE
                """
            ),
            active_code_params,
        )
    ).rowcount

    backfilled = (
        await session.execute(
            text(
                """
                INSERT INTO employee_document_checklists
                    (employee_id, document_type_id, status, created_by_id, updated_by_id, created_at, updated_at)
                SELECT
                    e.id,
                    d.id,
                    'not_submitted',
                    NULL,
                    NULL,
                    :now,
                    :now
                FROM employees e
                CROSS JOIN document_checklist_types d
                LEFT JOIN employee_document_checklists c
                    ON c.employee_id = e.id
                   AND c.document_type_id = d.id
                WHERE d.is_active = TRUE
                  AND c.id IS NULL
                """
            ),
            {"now": now},
        )
    ).rowcount

    return {
        "inserted": inserted,
        "updated": updated,
        "deactivated": deactivated,
        "backfilled": backfilled,
    }
