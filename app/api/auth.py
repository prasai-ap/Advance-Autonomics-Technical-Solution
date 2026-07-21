from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import FailedLoginLimiter
from app.db.database import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.services import authentication

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()
login_limiter = FailedLoginLimiter(settings.login_max_failures, settings.login_window_seconds)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    return authentication.register(db, data)


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    limited, retry_after = login_limiter.is_limited(client_ip)
    if limited:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many failed login attempts",
            headers={"Retry-After": str(retry_after)},
        )
    try:
        token = authentication.authenticate(db, str(data.email), data.password)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            limited, retry_after = login_limiter.record_failure(client_ip)
            if limited:
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    "Too many failed login attempts",
                    headers={"Retry-After": str(retry_after)},
                ) from exc
        raise
    login_limiter.clear(client_ip)
    return TokenResponse(access_token=token)
