from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.claim import Claim, ClaimStatus
from app.models.user import User
from app.repositories import claims
from app.schemas.claim import ClaimCreate
from app.services.claim_access import ClaimAccessPolicy

policy = ClaimAccessPolicy()


def create_claim(db: Session, user: User, data: ClaimCreate) -> Claim:
    claim = Claim(user_id=user.id, title=data.title, amount=data.amount, status=ClaimStatus.PENDING)
    claims.add(db, claim)
    db.commit()
    return claim


def list_claims(db: Session, user: User) -> list[Claim]:
    statement = policy.build_visibility_statement(user).order_by(
        Claim.created_at.desc(), Claim.id.desc()
    )
    return claims.list_from_statement(db, statement)


def get_claim(db: Session, user: User, claim_id: int) -> Claim:
    claim = claims.get_by_id(db, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    policy.ensure_can_view_claim(user, claim)
    return claim


def change_status(db: Session, user: User, claim_id: int, new_status: ClaimStatus) -> Claim:
    claim = claims.get_by_id(db, claim_id)
    if claim is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Claim not found")
    policy.ensure_can_change_status(user, claim)
    if claim.status != ClaimStatus.PENDING:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only pending claims can be updated")
    if not claims.transition_pending(db, claim.id, new_status):
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Claim status changed concurrently")
    db.commit()
    db.refresh(claim)
    return claim
