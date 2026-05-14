from fastapi.testclient import TestClient


import pytest

_ADMIN_EMAIL = "admin@hrms.local"
_ADMIN_PASSWORD = "Hrms@2026"


def _admin(client: TestClient) -> dict:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": _ADMIN_EMAIL, "password": _ADMIN_PASSWORD},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session", autouse=True)
def seed_official_locations(client: TestClient):
    resp = client.post("/api/v1/admin-units/import", json={
        "system_type": "new",
        "source_name": "official_import",
        "source_version": "qd19_2025",
        "mode": "merge",
    }, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    resp_old = client.post("/api/v1/admin-units/import", json={
        "system_type": "old",
        "source_name": "official_import_old",
        "source_version": "legacy_3_level",
        "mode": "merge",
    }, headers=_admin(client))
    assert resp_old.status_code == 200, resp_old.text
    yield


def test_list_address_systems(client: TestClient):
    resp = client.get("/api/v1/address-systems", headers=_admin(client))
    assert resp.status_code == 200
    data = resp.json()
    codes = {item["code"] for item in data}
    assert {"old", "new"} <= codes


def test_list_provinces_new_system(client: TestClient):
    resp = client.get("/api/v1/locations/provinces", params={"system_type": "new"}, headers=_admin(client))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["code"] == "25" for item in data)


def test_list_provinces_old_system(client: TestClient):
    resp = client.get("/api/v1/locations/provinces", params={"system_type": "old"}, headers=_admin(client))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["source_code"] == "01" for item in data)


def test_list_children_new_system(client: TestClient):
    provinces = client.get("/api/v1/locations/provinces", params={"system_type": "new"}, headers=_admin(client)).json()
    hanoi = next(item for item in provinces if item["code"] == "25")

    resp = client.get("/api/v1/locations/children", params={
        "system_type": "new",
        "parent_id": hanoi["id"],
    }, headers=_admin(client))
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["province_code"] == "25" for item in data)


def test_search_locations(client: TestClient):
    resp = client.get("/api/v1/locations/search", params={
        "system_type": "new",
        "keyword": "Ba Đình",
    }, headers=_admin(client))
    assert resp.status_code == 200
    assert any("Ba Đình" in item["name"] for item in resp.json())


def test_validate_location_path_success(client: TestClient):
    provinces = client.get("/api/v1/locations/provinces", params={"system_type": "new"}, headers=_admin(client)).json()
    hanoi = next(item for item in provinces if item["code"] == "25")
    children = client.get("/api/v1/locations/children", params={
        "system_type": "new",
        "parent_id": hanoi["id"],
    }, headers=_admin(client)).json()
    ward = next(item for item in children if item["code"] == "00004")

    resp = client.post("/api/v1/locations/validate-path", json={
        "system_type": "new",
        "province_unit_id": hanoi["id"],
        "ward_unit_id": ward["id"],
    }, headers=_admin(client))
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True


def test_validate_location_path_failure(client: TestClient):
    provinces = client.get("/api/v1/locations/provinces", params={"system_type": "new"}, headers=_admin(client)).json()
    hanoi = next(item for item in provinces if item["code"] == "25")
    an_giang = next(item for item in provinces if item["code"] == "01")
    children = client.get("/api/v1/locations/children", params={
        "system_type": "new",
        "parent_id": hanoi["id"],
    }, headers=_admin(client)).json()
    ward = next(item for item in children if item["code"] == "00004")

    resp = client.post("/api/v1/locations/validate-path", json={
        "system_type": "new",
        "province_unit_id": an_giang["id"],
        "ward_unit_id": ward["id"],
    }, headers=_admin(client))
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False


def test_validate_location_path_old_system_success(client: TestClient):
    provinces = client.get("/api/v1/locations/provinces", params={"system_type": "old"}, headers=_admin(client)).json()
    hanoi = next(item for item in provinces if item["source_code"] == "01")
    districts = client.get("/api/v1/locations/children", params={
        "system_type": "old",
        "parent_id": hanoi["id"],
    }, headers=_admin(client)).json()
    ba_dinh = next(item for item in districts if item["source_code"] == "001")
    wards = client.get("/api/v1/locations/children", params={
        "system_type": "old",
        "parent_id": ba_dinh["id"],
    }, headers=_admin(client)).json()
    truc_bach = next(item for item in wards if item["source_code"] == "00004")

    resp = client.post("/api/v1/locations/validate-path", json={
        "system_type": "old",
        "province_unit_id": hanoi["id"],
        "district_unit_id": ba_dinh["id"],
        "ward_unit_id": truc_bach["id"],
    }, headers=_admin(client))
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True


def test_validate_dual_location_paths_success(client: TestClient):
    new_provinces = client.get("/api/v1/locations/provinces", params={"system_type": "new"}, headers=_admin(client)).json()
    new_hanoi = next(item for item in new_provinces if item["code"] == "25")
    new_wards = client.get("/api/v1/locations/children", params={
        "system_type": "new",
        "parent_id": new_hanoi["id"],
    }, headers=_admin(client)).json()
    ba_dinh_ward_new = next(item for item in new_wards if item["code"] == "00004")

    old_provinces = client.get("/api/v1/locations/provinces", params={"system_type": "old"}, headers=_admin(client)).json()
    old_hanoi = next(item for item in old_provinces if item["source_code"] == "01")
    old_districts = client.get("/api/v1/locations/children", params={
        "system_type": "old",
        "parent_id": old_hanoi["id"],
    }, headers=_admin(client)).json()
    ba_dinh_district_old = next(item for item in old_districts if item["source_code"] == "001")
    old_wards = client.get("/api/v1/locations/children", params={
        "system_type": "old",
        "parent_id": ba_dinh_district_old["id"],
    }, headers=_admin(client)).json()
    truc_bach_ward_old = next(item for item in old_wards if item["source_code"] == "00004")

    resp = client.post("/api/v1/locations/validate-dual-paths", json={
        "old_address": {
            "system_type": "old",
            "province_unit_id": old_hanoi["id"],
            "district_unit_id": ba_dinh_district_old["id"],
            "ward_unit_id": truc_bach_ward_old["id"],
        },
        "new_address": {
            "system_type": "new",
            "province_unit_id": new_hanoi["id"],
            "ward_unit_id": ba_dinh_ward_new["id"],
        },
    }, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["valid"] is True
    assert body["old_address"]["valid"] is True
    assert body["new_address"]["valid"] is True


def test_validate_dual_location_paths_partial_failure(client: TestClient):
    new_provinces = client.get("/api/v1/locations/provinces", params={"system_type": "new"}, headers=_admin(client)).json()
    new_hanoi = next(item for item in new_provinces if item["code"] == "25")
    new_an_giang = next(item for item in new_provinces if item["code"] == "01")
    new_wards = client.get("/api/v1/locations/children", params={
        "system_type": "new",
        "parent_id": new_hanoi["id"],
    }, headers=_admin(client)).json()
    ba_dinh_ward_new = next(item for item in new_wards if item["code"] == "00004")

    old_provinces = client.get("/api/v1/locations/provinces", params={"system_type": "old"}, headers=_admin(client)).json()
    old_hanoi = next(item for item in old_provinces if item["source_code"] == "01")
    old_districts = client.get("/api/v1/locations/children", params={
        "system_type": "old",
        "parent_id": old_hanoi["id"],
    }, headers=_admin(client)).json()
    ba_dinh_district_old = next(item for item in old_districts if item["source_code"] == "001")
    old_wards = client.get("/api/v1/locations/children", params={
        "system_type": "old",
        "parent_id": ba_dinh_district_old["id"],
    }, headers=_admin(client)).json()
    truc_bach_ward_old = next(item for item in old_wards if item["source_code"] == "00004")

    resp = client.post("/api/v1/locations/validate-dual-paths", json={
        "old_address": {
            "system_type": "old",
            "province_unit_id": old_hanoi["id"],
            "district_unit_id": ba_dinh_district_old["id"],
            "ward_unit_id": truc_bach_ward_old["id"],
        },
        "new_address": {
            "system_type": "new",
            "province_unit_id": new_an_giang["id"],
            "ward_unit_id": ba_dinh_ward_new["id"],
        },
    }, headers=_admin(client))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["valid"] is False
    assert body["old_address"]["valid"] is True
    assert body["new_address"]["valid"] is False
