from app.seeds import administrative_units as seed
from app.seeds import old_administrative_units as old_seed


def test_build_province_rows_has_expected_count_and_codes():
    rows = seed.build_province_rows()
    assert len(rows) == 34
    assert rows[0]["name"] == "Tỉnh An Giang"
    assert rows[0]["code"] == "01"
    assert rows[-1]["name"] == "Tỉnh Vĩnh Long"
    assert rows[-1]["code"] == "96"


def test_normalize_and_type_mapping_handles_combining_unicode():
    assert seed.normalize_text("Phường") == "phuong"
    assert seed.normalize_text("Xã") == "xa"
    assert seed.map_ward_type("Phường") == "ward"
    assert seed.map_ward_type("Xã") == "ward"
    assert seed.map_ward_type("Đặc khu") == "ward"


def test_load_ward_rows_from_official_json_path():
    rows = seed.load_ward_rows(seed.settings.ADMINISTRATIVE_WARDS_JSON_PATH)
    assert len(rows) == 3321
    assert rows[0]["code"] == "00004"
    assert rows[0]["unit_type"] == "ward"
    assert rows[0]["province_code"] == "25"
    assert rows[0]["source_version"] == seed.SOURCE_VERSION


def test_convert_old_xlsx_rows_to_json_rows():
    result = old_seed.convert_xlsx_rows(old_seed.settings.ADMINISTRATIVE_OLD_UNITS_XLSX_PATH)
    rows = result.rows
    assert len(rows) == 10030
    assert len(result.conflicts) == 3
    assert result.conflicts[0]["ward_code"] == "00553"
    assert {
        "province_name": "Thành phố Hà Nội",
        "province_code": "01",
        "district_name": "Quận Ba Đình",
        "district_code": "001",
        "ward_name": "Phường Trúc Bạch",
        "ward_code": "00004",
    } in rows


def test_load_old_rows_from_generated_json_path():
    rows = old_seed.load_old_rows(old_seed.settings.ADMINISTRATIVE_OLD_UNITS_JSON_PATH)
    assert len(rows) == 10030
    assert rows[0]["province_code"] == "01"
    assert rows[0]["district_code"] == "001"
    assert rows[0]["ward_code"] == "00001"


def test_load_old_conflicts_from_generated_json_path():
    conflicts = old_seed.load_old_conflicts(old_seed.settings.ADMINISTRATIVE_OLD_UNITS_CONFLICTS_JSON_PATH)
    assert len(conflicts) == 3
    assert conflicts[0]["ward_code"] == "00553"
    assert len(conflicts[0]["variants"]) == 2
