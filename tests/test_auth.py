from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token


def test_login_and_me_are_safe(client: TestClient, users) -> None:
    response = client.post(
        "/auth/login", json={"email": "emp1@test.com", "password": "Employee@123"}
    )
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert "password" not in response.text
    me = client.get("/me", headers={"Authorization": f"Bearer {response.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["role"] == "EMPLOYEE"
    assert "password" not in me.text


def test_generic_login_failure(client: TestClient, users) -> None:
    unknown = client.post("/auth/login", json={"email": "none@test.com", "password": "bad"})
    wrong = client.post("/auth/login", json={"email": "emp1@test.com", "password": "bad"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json() == {"detail": "Invalid email or password"}


def test_registration_forbids_privileged_fields_and_duplicates(client: TestClient) -> None:
    malicious = client.post(
        "/auth/register",
        json={"email": "new@test.com", "password": "Password123", "role": "ADMIN"},
    )
    assert malicious.status_code == 422
    created = client.post(
        "/auth/register", json={"email": "NEW@test.com", "password": "Password123"}
    )
    assert created.status_code == 201
    assert created.json()["role"] == "EMPLOYEE"
    assert "password" not in created.text
    assert (
        client.post(
            "/auth/register", json={"email": "new@test.com", "password": "Password123"}
        ).status_code
        == 409
    )


def test_invalid_tokens_and_deleted_user(client: TestClient, db: Session, users) -> None:
    assert client.get("/me").status_code == 401
    assert client.get("/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    valid = create_access_token(users["emp1"].id)
    tampered = valid[:-1] + ("a" if valid[-1] != "a" else "b")
    assert client.get("/me", headers={"Authorization": f"Bearer {tampered}"}).status_code == 401
    settings = get_settings()
    expired = jwt.encode(
        {"sub": str(users["emp1"].id), "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    invalid_sub = jwt.encode(
        {"sub": "abc", "exp": datetime.now(timezone.utc) + timedelta(minutes=1)},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    for token in (expired, invalid_sub):
        assert client.get("/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    db.delete(users["emp1"])
    db.commit()
    assert client.get("/me", headers={"Authorization": f"Bearer {valid}"}).status_code == 401


def test_sixth_failed_login_is_limited_and_success_clears(client: TestClient, users) -> None:
    for _ in range(5):
        assert (
            client.post(
                "/auth/login", json={"email": "emp1@test.com", "password": "wrong"}
            ).status_code
            == 401
        )
    sixth = client.post("/auth/login", json={"email": "emp1@test.com", "password": "wrong"})
    assert sixth.status_code == 429
    assert "Retry-After" in sixth.headers


def test_success_clears_failures(client: TestClient, users) -> None:
    for _ in range(4):
        client.post("/auth/login", json={"email": "emp1@test.com", "password": "wrong"})
    assert (
        client.post(
            "/auth/login", json={"email": "emp1@test.com", "password": "Employee@123"}
        ).status_code
        == 200
    )
    assert (
        client.post("/auth/login", json={"email": "emp1@test.com", "password": "wrong"}).status_code
        == 401
    )
