"""Bootstrap seed cho danh mục hành chính hệ mới."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import administrative_import_service as service

SOURCE_NAME = "official_import"
SOURCE_VERSION = "qd19_2025"
SOURCE_LEGAL_BASIS = "Quyết định 19/2025/QĐ-TTg"
SYSTEM_TYPE = "new"
EFFECTIVE_FROM = service.DEFAULT_EFFECTIVE_FROM
PROVINCE_NAMES = service.DEFAULT_PROVINCE_NAMES

normalize_text = service.normalize_text
make_province_code = service.make_province_code
map_ward_type = service.map_ward_type


def build_province_rows() -> list[dict]:
    return service.build_province_rows(
        PROVINCE_NAMES,
        source_name=SOURCE_NAME,
        source_version=SOURCE_VERSION,
        effective_from=EFFECTIVE_FROM,
    )


def load_ward_rows(json_path: str):
    raw_rows = service.load_json_rows(json_path)
    province_map = {name: make_province_code(name) for name in PROVINCE_NAMES}
    return [
        service.build_new_system_ward_row(
            item,
            province_code=province_map[item["province_name"].strip()],
            source_name=SOURCE_NAME,
            source_version=SOURCE_VERSION,
            effective_from=EFFECTIVE_FROM,
        )
        for item in raw_rows
    ]


async def seed_new_administrative_system(
    session: AsyncSession,
    json_path: str | None = None,
) -> tuple[int, int]:
    result = await service.import_new_system_from_json(
        session,
        json_path=json_path or settings.ADMINISTRATIVE_WARDS_JSON_PATH,
        province_names=PROVINCE_NAMES,
        source_name=SOURCE_NAME,
        source_version=SOURCE_VERSION,
        effective_from=EFFECTIVE_FROM,
        file_name="wards_all_qd19_2025.json",
        mode="merge",
    )
    return result.success_rows + len(PROVINCE_NAMES), result.success_rows
