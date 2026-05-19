from fastapi.testclient import TestClient

BASE = "/api/v1/departments"


def _delete_by_code(client: TestClient, code: str) -> None:
    resp = client.get(BASE)
    assert resp.status_code == 200, resp.text
    for item in resp.json():
        if item["code"] == code:
            client.delete(f"{BASE}/{item['id']}")


def test_create_department_persists_display_prefix(client: TestClient):
    code = "TEST_DEPT_PREFIX_1"
    _delete_by_code(client, code)

    resp = client.post(
        BASE,
        json={
            "code": code,
            "name": "Test Department Prefix",
            "dept_type": "PHONG",
            "display_prefix": " cnt ",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["display_prefix"] == "CNT"

    _delete_by_code(client, code)


def test_update_department_display_prefix_can_be_changed_and_cleared(client: TestClient):
    code = "TEST_DEPT_PREFIX_2"
    _delete_by_code(client, code)

    created = client.post(
        BASE,
        json={
            "code": code,
            "name": "Test Department Prefix 2",
            "dept_type": "PHONG",
            "display_prefix": "abc",
        },
    )
    assert created.status_code == 201, created.text
    dept_id = created.json()["id"]
    assert created.json()["display_prefix"] == "ABC"

    updated = client.put(
        f"{BASE}/{dept_id}",
        json={"display_prefix": " pk "},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["display_prefix"] == "PK"

    cleared = client.put(
        f"{BASE}/{dept_id}",
        json={"display_prefix": "   "},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["display_prefix"] is None

    _delete_by_code(client, code)
