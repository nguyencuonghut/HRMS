from app.seeds import administrative_units as seed


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
