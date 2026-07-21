from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings, get_settings

password_hasher = PasswordHash.recommended()
_dummy_hash = password_hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def dummy_verify(password: str) -> None:
    password_hasher.verify(password, _dummy_hash)


def create_access_token(user_id: int, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expires},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "exp"], "verify_signature": True, "verify_exp": True},
    )
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject.isdigit() or int(subject) <= 0:
        raise jwt.InvalidTokenError("Invalid subject")
    return int(subject)
