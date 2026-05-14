import json

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services import administrative_import_service as service


def _make_session():
    engine = create_async_engine(settings.DATABASE_URL, connect_args={"ssl": False})
    return async_sessionmaker(engine, expire_on_commit=False)


async def _execute(sql: str, **params) -> None:
    async with _make_session()() as s:
        await s.execute(text(sql), params)
        await s.commit()


async def _scalar(sql: str, **params):
    async with _make_session()() as s:
        return (await s.execute(text(sql), params)).scalar()


async def _row(sql: str, **params):
    async with _make_session()() as s:
        return (await s.execute(text(sql), params)).first()


@pytest.fixture(autouse=True)
async def cleanup_import_data():
    await _execute("DELETE FROM administrative_import_errors")
    await _execute("DELETE FROM administrative_import_batches")
    await _execute(
        """
        DELETE FROM administrative_hierarchies
        WHERE system_type IN ('new', 'old')
          AND (
            child_unit_id IN (
              SELECT id FROM administrative_units WHERE source_name = 'test_import'
            )
            OR parent_unit_id IN (
              SELECT id FROM administrative_units WHERE source_name = 'test_import'
            )
          )
        """
    )
    await _execute("DELETE FROM administrative_units WHERE source_name = 'test_import'")
    yield
    await _execute("DELETE FROM administrative_import_errors")
    await _execute("DELETE FROM administrative_import_batches")
    await _execute(
        """
        DELETE FROM administrative_hierarchies
        WHERE system_type IN ('new', 'old')
          AND (
            child_unit_id IN (
              SELECT id FROM administrative_units WHERE source_name = 'test_import'
            )
            OR parent_unit_id IN (
              SELECT id FROM administrative_units WHERE source_name = 'test_import'
            )
          )
        """
    )
    await _execute("DELETE FROM administrative_units WHERE source_name = 'test_import'")


async def test_import_new_system_json_success(tmp_path):
    path = tmp_path / "wards.json"
    path.write_text(json.dumps([
        {
            "code": "990001",
            "name": "Phường Test Một",
            "type": "Phường",
            "province_name": "Thành phố Hà Nội",
            "legal_basis": "QĐ test",
        },
        {
            "code": "990002",
            "name": "Xã Test Hai",
            "type": "Xã",
            "province_name": "Tỉnh An Giang",
            "legal_basis": "QĐ test",
        },
    ], ensure_ascii=False), encoding="utf-8")

    async with _make_session()() as session:
        result = await service.import_new_system_from_json(
            session,
            json_path=path,
            source_name="test_import",
            source_version="v1",
            file_name=path.name,
            mode="merge",
        )

    assert result.batch_status == "success"
    assert result.total_rows == 2
    assert result.success_rows == 2
    assert result.failed_rows == 0

    unit_count = await _scalar(
        "SELECT COUNT(*) FROM administrative_units WHERE source_name = 'test_import'"
    )
    hier_count = await _scalar(
        """
        SELECT COUNT(*) FROM administrative_hierarchies ah
        JOIN administrative_units u ON u.id = ah.child_unit_id
        WHERE ah.system_type = 'new' AND u.source_name = 'test_import'
        """
    )
    batch = await _row(
        """
        SELECT status, total_rows, success_rows, failed_rows
        FROM administrative_import_batches
        WHERE source_name = 'test_import' AND source_version = 'v1'
        """
    )

    assert unit_count == 36
    assert hier_count == 2
    assert batch.status == "success"
    assert batch.total_rows == 2
    assert batch.success_rows == 2
    assert batch.failed_rows == 0


async def test_import_new_system_json_logs_errors_and_keeps_valid_rows(tmp_path):
    path = tmp_path / "wards-mixed.json"
    path.write_text(json.dumps([
        {
            "code": "990011",
            "name": "Phường Hợp Lệ",
            "type": "Phường",
            "province_name": "Thành phố Hà Nội",
            "legal_basis": "QĐ test",
        },
        {
            "code": "990012",
            "name": "Phường Lỗi",
            "type": "Phường",
            "province_name": "Tỉnh Không Tồn Tại",
            "legal_basis": "QĐ test",
        },
    ], ensure_ascii=False), encoding="utf-8")

    async with _make_session()() as session:
        result = await service.import_new_system_from_json(
            session,
            json_path=path,
            source_name="test_import",
            source_version="v_mixed",
            file_name=path.name,
            mode="merge",
        )

    assert result.batch_status == "failed"
    assert result.total_rows == 2
    assert result.success_rows == 1
    assert result.failed_rows == 1

    error_count = await _scalar("SELECT COUNT(*) FROM administrative_import_errors")
    hier_count = await _scalar(
        """
        SELECT COUNT(*) FROM administrative_hierarchies ah
        JOIN administrative_units u ON u.id = ah.child_unit_id
        WHERE ah.system_type = 'new' AND u.source_name = 'test_import' AND u.unit_type = 'ward'
        """
    )
    error_row = await _row(
        "SELECT error_message FROM administrative_import_errors ORDER BY id LIMIT 1"
    )

    assert error_count == 1
    assert hier_count == 1
    assert "Tỉnh/thành" in error_row.error_message


async def test_import_replace_deactivates_missing_units_and_rebuilds_hierarchy(tmp_path):
    path_v1 = tmp_path / "wards-v1.json"
    path_v1.write_text(json.dumps([
        {
            "code": "990021",
            "name": "Phường Replace Một",
            "type": "Phường",
            "province_name": "Thành phố Hà Nội",
            "legal_basis": "QĐ test",
        },
        {
            "code": "990022",
            "name": "Phường Replace Hai",
            "type": "Phường",
            "province_name": "Thành phố Hà Nội",
            "legal_basis": "QĐ test",
        },
    ], ensure_ascii=False), encoding="utf-8")

    path_v2 = tmp_path / "wards-v2.json"
    path_v2.write_text(json.dumps([
        {
            "code": "990021",
            "name": "Phường Replace Một",
            "type": "Phường",
            "province_name": "Thành phố Hà Nội",
            "legal_basis": "QĐ test",
        },
    ], ensure_ascii=False), encoding="utf-8")

    async with _make_session()() as session:
        await service.import_new_system_from_json(
            session,
            json_path=path_v1,
            source_name="test_import",
            source_version="v_replace",
            file_name=path_v1.name,
            mode="merge",
        )

    async with _make_session()() as session:
        result = await service.import_new_system_from_json(
            session,
            json_path=path_v2,
            source_name="test_import",
            source_version="v_replace",
            file_name=path_v2.name,
            mode="replace",
        )

    assert result.batch_status == "success"
    assert result.success_rows == 1

    active_ward_count = await _scalar(
        """
        SELECT COUNT(*) FROM administrative_units
        WHERE source_name = 'test_import' AND source_version = 'v_replace'
          AND unit_type = 'ward' AND is_active = true
        """
    )
    inactive_missing = await _scalar(
        """
        SELECT COUNT(*) FROM administrative_units
        WHERE code = '990022' AND source_name = 'test_import' AND is_active = false
        """
    )
    hier_count = await _scalar(
        """
        SELECT COUNT(*) FROM administrative_hierarchies ah
        JOIN administrative_units u ON u.id = ah.child_unit_id
        WHERE ah.system_type = 'new'
          AND u.source_name = 'test_import'
          AND u.source_version = 'v_replace'
          AND u.is_active = true
        """
    )

    assert active_ward_count == 1
    assert inactive_missing == 1
    assert hier_count == 1


async def test_import_old_system_json_success(tmp_path):
    path = tmp_path / "old-system.json"
    path.write_text(json.dumps([
        {
            "province_name": "Thành phố Hà Nội",
            "province_code": "01",
            "district_name": "Quận Ba Đình",
            "district_code": "001",
            "ward_name": "Phường Trúc Bạch",
            "ward_code": "00004",
        },
        {
            "province_name": "Thành phố Hà Nội",
            "province_code": "01",
            "district_name": "Quận Ba Đình",
            "district_code": "001",
            "ward_name": "Phường Quán Thánh",
            "ward_code": "00013",
        },
    ], ensure_ascii=False), encoding="utf-8")

    async with _make_session()() as session:
        result = await service.import_old_system_from_json(
            session,
            json_path=path,
            source_name="test_import",
            source_version="v_old",
            file_name=path.name,
            mode="merge",
        )

    assert result.batch_status == "success"
    assert result.total_rows == 2
    assert result.success_rows == 2
    assert result.failed_rows == 0

    unit_count = await _scalar(
        "SELECT COUNT(*) FROM administrative_units WHERE source_name = 'test_import' AND source_version = 'v_old'"
    )
    hier_count = await _scalar(
        """
        SELECT COUNT(*) FROM administrative_hierarchies ah
        JOIN administrative_units u ON u.id = ah.child_unit_id
        WHERE ah.system_type = 'old'
          AND u.source_name = 'test_import'
          AND u.source_version = 'v_old'
        """
    )
    province_row = await _row(
        """
        SELECT code, source_code, province_code
        FROM administrative_units
        WHERE source_name = 'test_import'
          AND source_version = 'v_old'
          AND unit_type = 'province'
        LIMIT 1
        """
    )
    ward_row = await _row(
        """
        SELECT code, source_code, province_code
        FROM administrative_units
        WHERE source_name = 'test_import'
          AND source_version = 'v_old'
          AND unit_type = 'ward'
          AND source_code = '00004'
        LIMIT 1
        """
    )

    assert unit_count == 4
    assert hier_count == 3
    assert province_row.code == "old:province:01"
    assert province_row.source_code == "01"
    assert province_row.province_code == "old:province:01"
    assert ward_row.code == "old:ward:00004"
    assert ward_row.source_code == "00004"
    assert ward_row.province_code == "old:province:01"


async def test_import_old_system_replace_deactivates_missing_units(tmp_path):
    path_v1 = tmp_path / "old-v1.json"
    path_v1.write_text(json.dumps([
        {
            "province_name": "Thành phố Hà Nội",
            "province_code": "01",
            "district_name": "Quận Ba Đình",
            "district_code": "001",
            "ward_name": "Phường Trúc Bạch",
            "ward_code": "00004",
        },
        {
            "province_name": "Thành phố Hà Nội",
            "province_code": "01",
            "district_name": "Quận Ba Đình",
            "district_code": "001",
            "ward_name": "Phường Quán Thánh",
            "ward_code": "00013",
        },
    ], ensure_ascii=False), encoding="utf-8")

    path_v2 = tmp_path / "old-v2.json"
    path_v2.write_text(json.dumps([
        {
            "province_name": "Thành phố Hà Nội",
            "province_code": "01",
            "district_name": "Quận Ba Đình",
            "district_code": "001",
            "ward_name": "Phường Trúc Bạch",
            "ward_code": "00004",
        },
    ], ensure_ascii=False), encoding="utf-8")

    async with _make_session()() as session:
        await service.import_old_system_from_json(
            session,
            json_path=path_v1,
            source_name="test_import",
            source_version="v_old_replace",
            file_name=path_v1.name,
            mode="merge",
        )

    async with _make_session()() as session:
        result = await service.import_old_system_from_json(
            session,
            json_path=path_v2,
            source_name="test_import",
            source_version="v_old_replace",
            file_name=path_v2.name,
            mode="replace",
        )

    assert result.batch_status == "success"
    assert result.success_rows == 1

    active_ward_count = await _scalar(
        """
        SELECT COUNT(*) FROM administrative_units
        WHERE source_name = 'test_import' AND source_version = 'v_old_replace'
          AND unit_type = 'ward' AND is_active = true
        """
    )
    inactive_missing = await _scalar(
        """
        SELECT COUNT(*) FROM administrative_units
        WHERE code = 'old:ward:00013'
          AND source_name = 'test_import'
          AND source_version = 'v_old_replace'
          AND is_active = false
        """
    )

    assert active_ward_count == 1
    assert inactive_missing == 1
