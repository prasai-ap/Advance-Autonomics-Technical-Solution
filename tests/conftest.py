from collections.abc import Generator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.auth import login_limiter
from app.core.security import hash_password
from app.db.database import Base, get_db
from app.main import create_app
from app.models.claim import Claim, ClaimStatus
from app.models.user import User, UserRole


@pytest.fixture
def db() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def users(db: Session) -> dict[str, User]:
    manager = User(
        email="manager@test.com",
        password_hash=hash_password("Manager@123"),
        role=UserRole.MANAGER,
    )
    admin = User(
        email="admin@test.com", password_hash=hash_password("Admin@123"), role=UserRole.ADMIN
    )
    emp1 = User(
        email="emp1@test.com", password_hash=hash_password("Employee@123"), role=UserRole.EMPLOYEE
    )
    emp2 = User(
        email="emp2@test.com", password_hash=hash_password("Employee@123"), role=UserRole.EMPLOYEE
    )
    emp3 = User(
        email="emp3@test.com", password_hash=hash_password("Employee@123"), role=UserRole.EMPLOYEE
    )
    db.add_all([manager, admin, emp1, emp2, emp3])
    db.flush()
    emp1.manager_id = manager.id
    emp2.manager_id = manager.id
    db.commit()
    return {user.email.split("@")[0]: user for user in (manager, admin, emp1, emp2, emp3)}


@pytest.fixture
def claims(db: Session, users: dict[str, User]) -> dict[str, Claim]:
    result = {}
    for key in ("emp1", "emp2", "emp3"):
        claim = Claim(
            user_id=users[key].id,
            title=f"{key} claim",
            amount=Decimal("25.50"),
            status=ClaimStatus.PENDING,
        )
        db.add(claim)
        result[key] = claim
    own = Claim(
        user_id=users["manager"].id,
        title="manager claim",
        amount=Decimal("10.00"),
        status=ClaimStatus.PENDING,
    )
    db.add(own)
    result["manager"] = own
    db.commit()
    return result


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    app = create_app(initialize_on_startup=False)

    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    login_limiter.reset()
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    login_limiter.reset()


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def auth_headers(client: TestClient, users: dict[str, User]) -> dict[str, dict[str, str]]:
    return {
        "emp1": login(client, "emp1@test.com", "Employee@123"),
        "manager": login(client, "manager@test.com", "Manager@123"),
        "admin": login(client, "admin@test.com", "Admin@123"),
    }
