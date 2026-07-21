from fastapi.testclient import TestClient


def test_employee_creation_is_server_owned(client: TestClient, auth_headers, users) -> None:
    response = client.post(
        "/claims", json={"title": "  Internet  ", "amount": "15.20"}, headers=auth_headers["emp1"]
    )
    assert response.status_code == 201
    assert response.json()["user_id"] == users["emp1"].id
    assert response.json()["status"] == "PENDING"
    for extra in ({"user_id": users["emp2"].id}, {"status": "APPROVED"}):
        payload = {"title": "bad", "amount": "1.00", **extra}
        assert client.post("/claims", json=payload, headers=auth_headers["emp1"]).status_code == 422


def test_employee_visibility_uses_403_for_existing_claim(client, auth_headers, claims) -> None:
    listing = client.get("/claims", headers=auth_headers["emp1"])
    assert {item["id"] for item in listing.json()} == {claims["emp1"].id}
    assert (
        client.get(f"/claims/{claims['emp2'].id}", headers=auth_headers["emp1"]).status_code == 403
    )
    assert client.get("/claims/99999", headers=auth_headers["emp1"]).status_code == 404


def test_manager_visibility_is_limited_to_direct_reports(client, auth_headers, claims) -> None:
    response = client.get("/claims", headers=auth_headers["manager"])
    assert {item["id"] for item in response.json()} == {
        claims["manager"].id,
        claims["emp1"].id,
        claims["emp2"].id,
    }
    assert (
        client.get(f"/claims/{claims['emp3'].id}", headers=auth_headers["manager"]).status_code
        == 403
    )


def test_admin_sees_all(client, auth_headers, claims) -> None:
    assert len(client.get("/claims", headers=auth_headers["admin"]).json()) == 4


def test_status_authorization_and_one_way_transition(client, auth_headers, claims) -> None:
    url = f"/claims/{claims['emp1'].id}/status"
    assert (
        client.patch(url, json={"status": "APPROVED"}, headers=auth_headers["emp1"]).status_code
        == 403
    )
    assert (
        client.patch(url, json={"status": "APPROVED"}, headers=auth_headers["manager"]).status_code
        == 200
    )
    assert (
        client.patch(url, json={"status": "REJECTED"}, headers=auth_headers["manager"]).status_code
        == 409
    )
    assert (
        client.patch(
            f"/claims/{claims['manager'].id}/status",
            json={"status": "APPROVED"},
            headers=auth_headers["manager"],
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/claims/{claims['emp3'].id}/status",
            json={"status": "APPROVED"},
            headers=auth_headers["manager"],
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/claims/{claims['emp2'].id}/status",
            json={"status": "PENDING"},
            headers=auth_headers["admin"],
        ).status_code
        == 422
    )


def test_claim_validation(client, auth_headers) -> None:
    for payload in (
        {"title": " ", "amount": "1.00"},
        {"title": "x", "amount": "0"},
        {"title": "x", "amount": "1.001"},
    ):
        assert client.post("/claims", json=payload, headers=auth_headers["emp1"]).status_code == 422
    assert client.get("/claims/0", headers=auth_headers["emp1"]).status_code == 422
