import logging
import time

from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.db.database import Base
from app.models.claim import Claim, ClaimStatus
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

SEED_USERS = (
    ("admin@test.com", "Admin@123", UserRole.ADMIN, None),
    ("manager@test.com", "Manager@123", UserRole.MANAGER, None),
    ("emp1@test.com", "Emp@123", UserRole.EMPLOYEE, "manager@test.com"),
    ("emp2@test.com", "Emp@123", UserRole.EMPLOYEE, "manager@test.com"),
    ("emp3@test.com", "Emp@123", UserRole.EMPLOYEE, None),
)


def seed_data(db: Session) -> None:
    by_email: dict[str, User] = {}
    for email, password, role, _ in SEED_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, password_hash=hash_password(password), role=role)
            db.add(user)
            db.flush()
        by_email[email] = user
    for email, _, _, manager_email in SEED_USERS:
        expected_manager = by_email.get(manager_email) if manager_email else None
        if by_email[email].manager_id != (expected_manager.id if expected_manager else None):
            by_email[email].manager = expected_manager
    for email in ("emp1@test.com", "emp2@test.com", "emp3@test.com"):
        title = f"Seed expense for {email}"
        exists = db.scalar(
            select(Claim.id).where(Claim.user_id == by_email[email].id, Claim.title == title)
        )
        if exists is None:
            db.add(
                Claim(
                    user_id=by_email[email].id,
                    title=title,
                    amount="100.00",
                    status=ClaimStatus.PENDING,
                )
            )
    db.commit()


def initialize_database(engine, session_factory, settings: Settings) -> None:
    for attempt in range(1, settings.database_startup_retries + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            Base.metadata.create_all(engine)
            with session_factory() as db:
                try:
                    seed_data(db)
                except Exception:
                    db.rollback()
                    raise
            logger.info("Database initialized")
            return
        except OperationalError:
            if attempt == settings.database_startup_retries:
                logger.exception("Database unavailable after bounded retries")
                raise
            logger.warning(
                "Database unavailable; retrying (%s/%s)", attempt, settings.database_startup_retries
            )
            time.sleep(settings.database_retry_delay_seconds)
