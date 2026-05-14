"""Seed dữ liệu danh mục hành chính cho hệ mới (tỉnh/thành → xã/phường).

Nguồn:
  - Danh mục 34 tỉnh/thành do dự án cung cấp
  - File JSON wards_all_qd19_2025.json do user chỉ định

Seeder này idempotent: chạy nhiều lần sẽ update dữ liệu theo code thay vì nhân bản.
"""

from __future__ import annotations

import datetime
import json
import unicodedata
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

SOURCE_NAME = "official_import"
SOURCE_VERSION = "qd19_2025"
SOURCE_LEGAL_BASIS = "Quyết định 19/2025/QĐ-TTg"
SYSTEM_TYPE = "new"
EFFECTIVE_FROM = datetime.date(2025, 1, 1)

PROVINCE_NAMES = [
    "Tỉnh An Giang",
    "Tỉnh Bắc Ninh",
    "Tỉnh Cà Mau",
    "Tỉnh Cao Bằng",
    "Thành phố Cần Thơ",
    "Thành phố Đà Nẵng",
    "Tỉnh Đắk Lắk",
    "Tỉnh Điện Biên",
    "Tỉnh Đồng Nai",
    "Tỉnh Đồng Tháp",
    "Tỉnh Gia Lai",
    "Thành phố Hà Nội",
    "Tỉnh Hà Tĩnh",
    "Thành phố Hải Phòng",
    "Thành phố Huế",
    "Tỉnh Hưng Yên",
    "Tỉnh Khánh Hòa",
    "Tỉnh Lai Châu",
    "Tỉnh Lạng Sơn",
    "Tỉnh Lào Cai",
    "Tỉnh Lâm Đồng",
    "Tỉnh Nghệ An",
    "Tỉnh Ninh Bình",
    "Tỉnh Phú Thọ",
    "Tỉnh Quảng Ngãi",
    "Tỉnh Quảng Ninh",
    "Tỉnh Quảng Trị",
    "Tỉnh Sơn La",
    "Tỉnh Tây Ninh",
    "Tỉnh Thái Nguyên",
    "Tỉnh Thanh Hóa",
    "Thành phố Hồ Chí Minh",
    "Tỉnh Tuyên Quang",
    "Tỉnh Vĩnh Long",
]


def normalize_text(value: str) -> str:
    """Chuẩn hóa chuỗi để search/map ổn định, bỏ khác biệt dấu tổ hợp."""
    value = unicodedata.normalize("NFC", value.strip())
    decomposed = unicodedata.normalize("NFD", value)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    without_marks = without_marks.replace("Đ", "D").replace("đ", "d")
    return " ".join(without_marks.lower().split())


def make_province_code(name: str) -> str:
    base = name.removeprefix("Tỉnh ").removeprefix("Thành phố ")
    normalized = normalize_text(base).replace(" ", "_")
    return f"PRV_{normalized.upper()}"


def map_ward_type(raw_type: str) -> str:
    normalized = normalize_text(raw_type)
    if normalized in {"xa", "phuong", "dac khu"}:
        return "ward"
    raise ValueError(f"Loại đơn vị không hỗ trợ: {raw_type}")


def build_province_rows() -> list[dict]:
    rows: list[dict] = []
    for name in PROVINCE_NAMES:
        code = make_province_code(name)
        rows.append({
            "code": code,
            "name": name,
            "normalized_name": normalize_text(name),
            "unit_type": "province",
            "official_name": name,
            "province_code": code,
            "is_active": True,
            "effective_from": EFFECTIVE_FROM,
            "effective_to": None,
            "source_name": SOURCE_NAME,
            "source_version": SOURCE_VERSION,
        })
    return rows


def load_ward_rows(json_path: str | Path) -> list[dict]:
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file seed xã/phường: {path}")

    with path.open("r", encoding="utf-8") as f:
        raw_rows = json.load(f)

    province_map = {name: make_province_code(name) for name in PROVINCE_NAMES}
    rows: list[dict] = []

    for item in raw_rows:
        province_name = unicodedata.normalize("NFC", item["province_name"].strip())
        province_code = province_map.get(province_name)
        if province_code is None:
            raise ValueError(f"Tỉnh/thành trong file seed không nằm trong danh mục cấu hình: {province_name}")

        name = unicodedata.normalize("NFC", item["name"].strip())
        rows.append({
            "code": str(item["code"]).strip(),
            "name": name,
            "normalized_name": normalize_text(name),
            "unit_type": map_ward_type(item["type"]),
            "official_name": name,
            "province_code": province_code,
            "is_active": True,
            "effective_from": EFFECTIVE_FROM,
            "effective_to": None,
            "source_name": SOURCE_NAME,
            "source_version": SOURCE_VERSION,
        })

    return rows


async def _unit_ids_by_code(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(text("SELECT code, id FROM administrative_units"))
    return {row.code: row.id for row in result}


async def seed_new_administrative_system(
    session: AsyncSession,
    json_path: str | None = None,
) -> tuple[int, int]:
    """Seed tỉnh/thành và xã/phường cho hệ hành chính mới.

    Returns:
      (units_upserted, hierarchies_inserted)
    """
    json_path = json_path or settings.ADMINISTRATIVE_WARDS_JSON_PATH
    province_rows = build_province_rows()
    ward_rows = load_ward_rows(json_path)
    all_rows = province_rows + ward_rows

    units_upserted = 0
    for row in all_rows:
        result = await session.execute(
            text("""
                INSERT INTO administrative_units (
                    code, name, normalized_name, unit_type, official_name, province_code,
                    is_active, effective_from, effective_to, source_name, source_version
                ) VALUES (
                    :code, :name, :normalized_name, :unit_type, :official_name, :province_code,
                    :is_active, :effective_from, :effective_to, :source_name, :source_version
                )
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    normalized_name = EXCLUDED.normalized_name,
                    unit_type = EXCLUDED.unit_type,
                    official_name = EXCLUDED.official_name,
                    province_code = EXCLUDED.province_code,
                    is_active = EXCLUDED.is_active,
                    effective_from = EXCLUDED.effective_from,
                    effective_to = EXCLUDED.effective_to,
                    source_name = EXCLUDED.source_name,
                    source_version = EXCLUDED.source_version,
                    updated_at = now()
            """),
            row,
        )
        units_upserted += result.rowcount

    unit_ids = await _unit_ids_by_code(session)
    hierarchies_inserted = 0

    for ward in ward_rows:
        parent_id = unit_ids[ward["province_code"]]
        child_id = unit_ids[ward["code"]]
        result = await session.execute(
            text("""
                INSERT INTO administrative_hierarchies (
                    system_type, parent_unit_id, child_unit_id, level_depth,
                    effective_from, effective_to, is_active
                ) VALUES (
                    :system_type, :parent_unit_id, :child_unit_id, :level_depth,
                    :effective_from, :effective_to, true
                )
                ON CONFLICT ON CONSTRAINT uq_admin_hier_path DO NOTHING
            """),
            {
                "system_type": SYSTEM_TYPE,
                "parent_unit_id": parent_id,
                "child_unit_id": child_id,
                "level_depth": 2,
                "effective_from": EFFECTIVE_FROM,
                "effective_to": None,
            },
        )
        hierarchies_inserted += result.rowcount

    return units_upserted, hierarchies_inserted
