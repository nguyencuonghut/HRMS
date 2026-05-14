"""Convert and seed old 3-level administrative catalog data."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services import administrative_import_service as service

SOURCE_NAME = "official_import_old"
SOURCE_VERSION = "legacy_3_level"
SYSTEM_TYPE = "old"
EFFECTIVE_FROM = service.DEFAULT_EFFECTIVE_FROM
NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


@dataclass
class ConversionResult:
    rows: list[dict]
    conflicts: list[dict]


def _load_shared_strings(xlsx_path: str | Path) -> list[str]:
    with zipfile.ZipFile(xlsx_path) as archive:
        raw = archive.read("xl/sharedStrings.xml")
    root = ET.fromstring(raw)
    values: list[str] = []
    for item in root.findall("main:si", NS):
        text_parts = [node.text or "" for node in item.findall(".//main:t", NS)]
        values.append("".join(text_parts))
    return values


def _read_sheet_rows(xlsx_path: str | Path) -> list[dict[str, str]]:
    shared_strings = _load_shared_strings(xlsx_path)
    with zipfile.ZipFile(xlsx_path) as archive:
        raw_sheet = archive.read("xl/worksheets/sheet1.xml")
    root = ET.fromstring(raw_sheet)

    rows: list[dict[str, str]] = []
    for row in root.findall("main:sheetData/main:row", NS):
        row_no = int(row.attrib["r"])
        if row_no <= 2:
            continue

        cells: dict[str, str] = {}
        for cell in row.findall("main:c", NS):
            ref = cell.attrib.get("r", "")
            column = "".join(ch for ch in ref if ch.isalpha())
            value_node = cell.find("main:v", NS)
            if not column or value_node is None or value_node.text is None:
                continue

            if cell.attrib.get("t") == "s":
                cells[column] = shared_strings[int(value_node.text)]
            else:
                cells[column] = value_node.text

        if {"A", "B", "C", "D"} <= set(cells):
            rows.append(cells)
    return rows


def convert_xlsx_rows(xlsx_path: str | Path) -> ConversionResult:
    first_seen_by_ward_code: dict[str, dict] = {}
    conflicts_by_ward_code: dict[str, list[dict]] = {}

    for row in _read_sheet_rows(xlsx_path):
        ward_name = service.normalize_display_text(row["A"])
        ward_code = service.normalize_display_text(row["B"])
        district_name, district_code = service.parse_name_and_code(row["C"], label="quận/huyện")
        province_name, province_code = service.parse_name_and_code(row["D"], label="tỉnh/thành")

        current = {
            "province_name": province_name,
            "province_code": province_code,
            "district_name": district_name,
            "district_code": district_code,
            "ward_name": ward_name,
            "ward_code": ward_code,
        }
        current_normalized = (
            province_code,
            service.normalize_text(province_name),
            district_code,
            service.normalize_text(district_name),
            service.normalize_text(ward_name),
        )

        existing = first_seen_by_ward_code.get(ward_code)
        if existing is None:
            first_seen_by_ward_code[ward_code] = current
            continue

        existing_normalized = (
            existing["province_code"],
            service.normalize_text(existing["province_name"]),
            existing["district_code"],
            service.normalize_text(existing["district_name"]),
            service.normalize_text(existing["ward_name"]),
        )
        if existing_normalized == current_normalized:
            continue

        conflicts = conflicts_by_ward_code.setdefault(ward_code, [existing])
        if current not in conflicts:
            conflicts.append(current)

    conflict_codes = set(conflicts_by_ward_code)
    output_rows = [
        row for code, row in first_seen_by_ward_code.items()
        if code not in conflict_codes
    ]

    output_rows.sort(
        key=lambda item: (
            item["province_code"],
            item["district_code"],
            item["ward_code"],
        )
    )
    conflicts = [
        {
            "ward_code": ward_code,
            "variants": conflicts_by_ward_code[ward_code],
        }
        for ward_code in sorted(conflicts_by_ward_code)
    ]
    return ConversionResult(rows=output_rows, conflicts=conflicts)


def convert_xlsx_rows_to_json_rows(xlsx_path: str | Path) -> list[dict]:
    return convert_xlsx_rows(xlsx_path).rows


def write_old_system_json(
    *,
    xlsx_path: str | Path | None = None,
    json_path: str | Path | None = None,
    conflicts_json_path: str | Path | None = None,
) -> Path:
    source_path = Path(xlsx_path or settings.ADMINISTRATIVE_OLD_UNITS_XLSX_PATH)
    target_path = Path(json_path or settings.ADMINISTRATIVE_OLD_UNITS_JSON_PATH)
    conflicts_path = Path(conflicts_json_path or settings.ADMINISTRATIVE_OLD_UNITS_CONFLICTS_JSON_PATH)
    result = convert_xlsx_rows(source_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(result.rows, ensure_ascii=False, indent=2), encoding="utf-8")
    conflicts_path.write_text(json.dumps(result.conflicts, ensure_ascii=False, indent=2), encoding="utf-8")
    return target_path


def load_old_rows(json_path: str | Path | None = None) -> list[dict]:
    return service.load_json_rows(json_path or settings.ADMINISTRATIVE_OLD_UNITS_JSON_PATH)


def load_old_conflicts(json_path: str | Path | None = None) -> list[dict]:
    return service.load_json_rows(json_path or settings.ADMINISTRATIVE_OLD_UNITS_CONFLICTS_JSON_PATH)


async def seed_old_administrative_system(
    session: AsyncSession,
    json_path: str | None = None,
) -> tuple[int, int]:
    result = await service.import_old_system_from_json(
        session,
        json_path=json_path or settings.ADMINISTRATIVE_OLD_UNITS_JSON_PATH,
        source_name=SOURCE_NAME,
        source_version=SOURCE_VERSION,
        effective_from=EFFECTIVE_FROM,
        file_name="old_administrative_units_3_level.json",
        mode="merge",
    )
    rows = load_old_rows(json_path)
    provinces = {item["province_code"] for item in rows}
    districts = {item["district_code"] for item in rows}
    return len(provinces) + len(districts) + result.success_rows, (len(districts) + result.success_rows)
