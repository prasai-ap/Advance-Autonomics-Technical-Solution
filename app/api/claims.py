from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User, UserRole
from app.schemas.claim import ClaimCreate, ClaimResponse, StatusUpdate
from app.services import claims

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("", response_model=ClaimResponse, status_code=status.HTTP_201_CREATED)
def create(
    data: ClaimCreate,
    current_user: User = Depends(require_roles(UserRole.EMPLOYEE)),
    db: Session = Depends(get_db),
) -> ClaimResponse:
    return claims.create_claim(db, current_user, data)


@router.get("", response_model=list[ClaimResponse])
def list_all(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ClaimResponse]:
    return claims.list_claims(db, current_user)


@router.get("/{claim_id}", response_model=ClaimResponse)
def retrieve(
    claim_id: Annotated[int, Path(gt=0)],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ClaimResponse:
    return claims.get_claim(db, current_user, claim_id)


@router.patch("/{claim_id}/status", response_model=ClaimResponse)
def update_status(
    claim_id: Annotated[int, Path(gt=0)],
    data: StatusUpdate,
    current_user: User = Depends(require_roles(UserRole.MANAGER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ClaimResponse:
    return claims.change_status(db, current_user, claim_id, data.status)
