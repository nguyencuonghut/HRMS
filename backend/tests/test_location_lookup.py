from fastapi.testclient import TestClient


import pytest


@pytest.fixture(scope="session", autouse=True)
def seed_official_locations(client: TestClient):
    resp = client.post("/api/v1/admin-units/import", json={
        "system_type": "new",
        "source_name": "official_import",
        "source_version": "qd19_2025",
        "mode": "merge",
    })
    assert resp.status_code == 200, resp.text
    yield


def test_list_address_systems(client: TestClient):
    resp = client.get("/api/v1/address-systems")
    assert resp.status_code == 200
    data = resp.json()
    codes = {item["code"] for item in data}
    assert {"old", "new"} <= codes


def test_list_provinces_new_system(client: TestClient):
    resp = client.get("/api/v1/locations/provinces", params={"system_type": "new"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["code"] == "PRV_HA_NOI" for item in data)


def test_list_children_new_system(client: TestClient):
    provinces = client.get("/api/v1/locations/provinces", params={"system_type": "new"}).json()
    hanoi = next(item for item in provinces if item["code"] == "PRV_HA_NOI")

    resp = client.get("/api/v1/locations/children", params={
        "system_type": "new",
        "parent_id": hanoi["id"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["province_code"] == "PRV_HA_NOI" for item in data)


def test_search_locations(client: TestClient):
    resp = client.get("/api/v1/locations/search", params={
        "system_type": "new",
        "keyword": "Ba Đình",
    })
    assert resp.status_code == 200
    assert any("Ba Đình" in item["name"] for item in resp.json())


def test_validate_location_path_success(client: TestClient):
    provinces = client.get("/api/v1/locations/provinces", params={"system_type": "new"}).json()
    hanoi = next(item for item in provinces if item["code"] == "PRV_HA_NOI")
    children = client.get("/api/v1/locations/children", params={
        "system_type": "new",
        "parent_id": hanoi["id"],
    }).json()
    ward = next(item for item in children if item["code"] == "00004")

    resp = client.post("/api/v1/locations/validate-path", json={
        "system_type": "new",
        "province_unit_id": hanoi["id"],
        "ward_unit_id": ward["id"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True


def test_validate_location_path_failure(client: TestClient):
    provinces = client.get("/api/v1/locations/provinces", params={"system_type": "new"}).json()
    hanoi = next(item for item in provinces if item["code"] == "PRV_HA_NOI")
    an_giang = next(item for item in provinces if item["code"] == "PRV_AN_GIANG")
    children = client.get("/api/v1/locations/children", params={
        "system_type": "new",
        "parent_id": hanoi["id"],
    }).json()
    ward = next(item for item in children if item["code"] == "00004")

    resp = client.post("/api/v1/locations/validate-path", json={
        "system_type": "new",
        "province_unit_id": an_giang["id"],
        "ward_unit_id": ward["id"],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False
