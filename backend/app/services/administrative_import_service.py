from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import unicodedata

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_EFFECTIVE_FROM = date(2025, 1, 1)
DEFAULT_PROVINCE_PAIRS = [
    ("01", "Tỉnh An Giang"),
    ("04", "Tỉnh Bắc Ninh"),
    ("08", "Tỉnh Cà Mau"),
    ("11", "Tỉnh Cao Bằng"),
    ("12", "Thành phố Cần Thơ"),
    ("14", "Thành phố Đà Nẵng"),
    ("15", "Tỉnh Đắk Lắk"),
    ("19", "Tỉnh Điện Biên"),
    ("20", "Tỉnh Đồng Nai"),
    ("22", "Tỉnh Đồng Tháp"),
    ("24", "Tỉnh Gia Lai"),
    ("25", "Thành phố Hà Nội"),
    ("31", "Tỉnh Hà Tĩnh"),
    ("33", "Thành phố Hải Phòng"),
    ("37", "Thành phố Huế"),
    ("38", "Tỉnh Hưng Yên"),
    ("40", "Tỉnh Khánh Hòa"),
    ("42", "Tỉnh Lai Châu"),
    ("44", "Tỉnh Lạng Sơn"),
    ("46", "Tỉnh Lào Cai"),
    ("48", "Tỉnh Lâm Đồng"),
    ("51", "Tỉnh Nghệ An"),
    ("52", "Tỉnh Ninh Bình"),
    ("56", "Tỉnh Phú Thọ"),
    ("66", "Tỉnh Quảng Ngãi"),
    ("68", "Tỉnh Quảng Ninh"),
    ("75", "Tỉnh Quảng Trị"),
    ("79", "Tỉnh Sơn La"),
    ("80", "Tỉnh Tây Ninh"),
    ("82", "Tỉnh Thái Nguyên"),
    ("86", "Tỉnh Thanh Hóa"),
    ("91", "Thành phố Hồ Chí Minh"),
    ("92", "Tỉnh Tuyên Quang"),
    ("96", "Tỉnh Vĩnh Long"),
]
DEFAULT_PROVINCE_NAMES = [name for _, name in DEFAULT_PROVINCE_PAIRS]
PROVINCE_CODE_BY_NAME = {name: code for code, name in DEFAULT_PROVINCE_PAIRS}


@dataclass
class AdministrativeImportResult:
    batch_id: int
    batch_status: str
    total_rows: int
    success_rows: int
    failed_rows: int


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFC", value.strip())
    decomposed = unicodedata.normalize("NFD", value)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    without_marks = without_marks.replace("Đ", "D").replace("đ", "d")
    return " ".join(without_marks.lower().split())


def make_province_code(name: str) -> str:
    normalized_name = unicodedata.normalize("NFC", name.strip())
    code = PROVINCE_CODE_BY_NAME.get(normalized_name)
    if code is None:
        raise ValueError(f"Không tìm thấy mã tỉnh/thành cho '{name}'")
    return code


def map_ward_type(raw_type: str) -> str:
    normalized = normalize_text(raw_type)
    if normalized in {"xa", "phuong", "dac khu"}:
        return "ward"
    raise ValueError(f"Loại đơn vị không hỗ trợ: {raw_type}")


def build_province_rows(
    province_names: list[str],
    *,
    source_name: str,
    source_version: str,
    effective_from: date,
) -> list[dict]:
    rows: list[dict] = []
    for name in province_names:
        code = make_province_code(name)
        rows.append({
            "code": code,
            "name": name,
            "normalized_name": normalize_text(name),
            "unit_type": "province",
            "official_name": name,
            "province_code": code,
            "is_active": True,
            "effective_from": effective_from,
            "effective_to": None,
            "source_name": source_name,
            "source_version": source_version,
        })
    return rows


def load_json_rows(json_path: str | Path) -> list[dict]:
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file import xã/phường: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_new_system_ward_row(
    item: dict,
    *,
    province_code: str,
    source_name: str,
    source_version: str,
    effective_from: date,
) -> dict:
    name = unicodedata.normalize("NFC", str(item["name"]).strip())
    return {
        "code": str(item["code"]).strip(),
        "name": name,
        "normalized_name": normalize_text(name),
        "unit_type": map_ward_type(str(item["type"])),
        "official_name": name,
        "province_code": province_code,
        "is_active": True,
        "effective_from": effective_from,
        "effective_to": None,
        "source_name": source_name,
        "source_version": source_version,
    }


async def _create_batch(
    session: AsyncSession,
    *,
    source_name: str,
    source_version: str,
    file_name: str | None,
    imported_by: int | None,
) -> int:
    result = await session.execute(
        text("""
            INSERT INTO administrative_import_batches (
                source_name, source_version, file_name, imported_by, status
            ) VALUES (
                :source_name, :source_version, :file_name, :imported_by, 'draft'
            )
            RETURNING id
        """),
        {
            "source_name": source_name,
            "source_version": source_version,
            "file_name": file_name,
            "imported_by": imported_by,
        },
    )
    return result.scalar_one()


async def _update_batch(
    session: AsyncSession,
    *,
    batch_id: int,
    status: str,
    total_rows: int,
    success_rows: int,
    failed_rows: int,
    error_summary: str | None,
) -> None:
    await session.execute(
        text("""
            UPDATE administrative_import_batches
            SET status = :status,
                total_rows = :total_rows,
                success_rows = :success_rows,
                failed_rows = :failed_rows,
                error_summary = :error_summary
            WHERE id = :batch_id
        """),
        {
            "batch_id": batch_id,
            "status": status,
            "total_rows": total_rows,
            "success_rows": success_rows,
            "failed_rows": failed_rows,
            "error_summary": error_summary,
        },
    )


async def _log_import_error(
    session: AsyncSession,
    *,
    batch_id: int,
    row_no: int,
    raw_payload: dict,
    error_message: str,
) -> None:
    await session.execute(
        text("""
            INSERT INTO administrative_import_errors (batch_id, row_no, raw_payload, error_message)
            VALUES (:batch_id, :row_no, CAST(:raw_payload AS jsonb), :error_message)
        """),
        {
            "batch_id": batch_id,
            "row_no": row_no,
            "raw_payload": json.dumps(raw_payload, ensure_ascii=False),
            "error_message": error_message,
        },
    )


async def _upsert_unit(session: AsyncSession, row: dict) -> int:
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
            RETURNING id
        """),
        row,
    )
    return result.scalar_one()


async def _delete_existing_hierarchies_for_source(
    session: AsyncSession,
    *,
    system_type: str,
    source_name: str,
    source_version: str,
) -> None:
    await session.execute(
        text("""
            DELETE FROM administrative_hierarchies
            WHERE system_type = :system_type
              AND child_unit_id IN (
                SELECT id FROM administrative_units
                WHERE source_name = :source_name
                  AND source_version = :source_version
                  AND unit_type = 'ward'
              )
        """),
        {
            "system_type": system_type,
            "source_name": source_name,
            "source_version": source_version,
        },
    )


async def _deactivate_missing_units_safe(
    session: AsyncSession,
    *,
    source_name: str,
    source_version: str,
    keep_codes: set[str],
) -> None:
    if keep_codes:
        placeholders = ", ".join(f":code_{i}" for i, _ in enumerate(sorted(keep_codes)))
        params = {
            "source_name": source_name,
            "source_version": source_version,
            **{f"code_{i}": code for i, code in enumerate(sorted(keep_codes))},
        }
        await session.execute(
            text(f"""
                UPDATE administrative_units
                SET is_active = false, updated_at = now()
                WHERE source_name = :source_name
                  AND source_version = :source_version
                  AND unit_type = 'ward'
                  AND code NOT IN ({placeholders})
            """),
            params,
        )
    else:
        await session.execute(
            text("""
                UPDATE administrative_units
                SET is_active = false, updated_at = now()
                WHERE source_name = :source_name
                  AND source_version = :source_version
                  AND unit_type = 'ward'
            """),
            {
                "source_name": source_name,
                "source_version": source_version,
            },
        )


async def _insert_hierarchy(
    session: AsyncSession,
    *,
    system_type: str,
    parent_unit_id: int,
    child_unit_id: int,
    level_depth: int,
    effective_from: date,
) -> None:
    await session.execute(
        text("""
            INSERT INTO administrative_hierarchies (
                system_type, parent_unit_id, child_unit_id, level_depth,
                effective_from, effective_to, is_active
            ) VALUES (
                :system_type, :parent_unit_id, :child_unit_id, :level_depth,
                :effective_from, NULL, true
            )
            ON CONFLICT ON CONSTRAINT uq_admin_hier_path DO NOTHING
        """),
        {
            "system_type": system_type,
            "parent_unit_id": parent_unit_id,
            "child_unit_id": child_unit_id,
            "level_depth": level_depth,
            "effective_from": effective_from,
        },
    )


async def import_new_system_from_json(
    session: AsyncSession,
    *,
    json_path: str | Path,
    province_names: list[str] | None = None,
    source_name: str,
    source_version: str,
    effective_from: date = DEFAULT_EFFECTIVE_FROM,
    file_name: str | None = None,
    imported_by: int | None = None,
    mode: str = "merge",
) -> AdministrativeImportResult:
    if mode not in {"merge", "replace"}:
        raise ValueError("mode phải là 'merge' hoặc 'replace'")
    province_names = province_names or DEFAULT_PROVINCE_NAMES

    batch_id = await _create_batch(
        session,
        source_name=source_name,
        source_version=source_version,
        file_name=file_name,
        imported_by=imported_by,
    )

    province_rows = build_province_rows(
        province_names,
        source_name=source_name,
        source_version=source_version,
        effective_from=effective_from,
    )
    province_map = {name: make_province_code(name) for name in province_names}
    province_ids: dict[str, int] = {}

    for row in province_rows:
        province_ids[row["code"]] = await _upsert_unit(session, row)

    raw_rows = load_json_rows(json_path)
    total_rows = len(raw_rows)
    success_rows = 0
    failed_rows = 0
    success_codes: set[str] = set()
    hierarchy_records: list[tuple[int, int]] = []
    error_messages: list[str] = []

    for index, item in enumerate(raw_rows, start=1):
        try:
            province_name = unicodedata.normalize("NFC", str(item["province_name"]).strip())
            province_code = province_map.get(province_name)
            if province_code is None:
                raise ValueError(
                    f"Tỉnh/thành trong file import không nằm trong danh mục cấu hình: {province_name}"
                )
            ward_row = build_new_system_ward_row(
                item,
                province_code=province_code,
                source_name=source_name,
                source_version=source_version,
                effective_from=effective_from,
            )
            ward_id = await _upsert_unit(session, ward_row)
            hierarchy_records.append((province_ids[province_code], ward_id))
            success_codes.add(ward_row["code"])
            success_rows += 1
        except Exception as exc:
            failed_rows += 1
            message = str(exc)
            error_messages.append(message)
            await _log_import_error(
                session,
                batch_id=batch_id,
                row_no=index,
                raw_payload=item,
                error_message=message,
            )

    if mode == "replace":
        await _delete_existing_hierarchies_for_source(
            session,
            system_type="new",
            source_name=source_name,
            source_version=source_version,
        )
        await _deactivate_missing_units_safe(
            session,
            source_name=source_name,
            source_version=source_version,
            keep_codes=success_codes,
        )

    for parent_id, child_id in hierarchy_records:
        await _insert_hierarchy(
            session,
            system_type="new",
            parent_unit_id=parent_id,
            child_unit_id=child_id,
            level_depth=2,
            effective_from=effective_from,
        )

    status = "failed" if failed_rows > 0 else "success"
    summary = "; ".join(error_messages[:5]) if error_messages else None
    await _update_batch(
        session,
        batch_id=batch_id,
        status=status,
        total_rows=total_rows,
        success_rows=success_rows,
        failed_rows=failed_rows,
        error_summary=summary,
    )
    await session.commit()

    return AdministrativeImportResult(
        batch_id=batch_id,
        batch_status=status,
        total_rows=total_rows,
        success_rows=success_rows,
        failed_rows=failed_rows,
    )
