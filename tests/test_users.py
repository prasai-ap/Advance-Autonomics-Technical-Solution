from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


def test_only_admin_deletes_and_cannot_delete_self(client, auth_headers, users) -> None:
    assert (
        client.delete(f"/users/{users['emp2'].id}", headers=auth_headers["emp1"]).status_code == 403
    )
    assert (
        client.delete(f"/users/{users['admin'].id}", headers=auth_headers["admin"]).status_code
        == 409
    )
    assert client.delete("/users/99999", headers=auth_headers["admin"]).status_code == 404
    assert (
        client.delete(f"/users/{users['emp2'].id}", headers=auth_headers["admin"]).status_code
        == 204
    )


def test_deleting_manager_nulls_reports(
    client: TestClient, db: Session, auth_headers, users
) -> None:
    manager_id = users["manager"].id
    assert client.delete(f"/users/{manager_id}", headers=auth_headers["admin"]).status_code == 204
    db.expire_all()
    assert db.get(User, users["emp1"].id).manager_id is None
