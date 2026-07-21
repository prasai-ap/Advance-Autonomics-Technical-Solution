from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, dummy_verify, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories import users
from app.schemas.user import UserCreate

INVALID_CREDENTIALS = HTTPException(
    status.HTTP_401_UNAUTHORIZED,
    "Invalid email or password",
    headers={"WWW-Authenticate": "Bearer"},
)


def register(db: Session, data: UserCreate) -> User:
    if users.get_by_email(db, str(data.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=str(data.email), password_hash=hash_password(data.password), role=UserRole.EMPLOYEE
    )
    try:
        users.add(db, user)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered") from exc
    return user


def authenticate(db: Session, email: str, password: str) -> str:
    user = users.get_by_email(db, email)
    if user is None:
        dummy_verify(password)
        raise INVALID_CREDENTIALS
    if not verify_password(password, user.password_hash):
        raise INVALID_CREDENTIALS
    return create_access_token(user.id)
