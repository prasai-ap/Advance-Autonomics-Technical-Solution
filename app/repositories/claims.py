from sqlalchemy import Select, select, update
from sqlalchemy.orm import Session

from app.models.claim import Claim, ClaimStatus


def get_by_id(db: Session, claim_id: int) -> Claim | None:
    return db.get(Claim, claim_id)


def list_from_statement(db: Session, statement: Select[tuple[Claim]]) -> list[Claim]:
    return list(db.scalars(statement))


def add(db: Session, claim: Claim) -> Claim:
    db.add(claim)
    db.flush()
    return claim


def transition_pending(db: Session, claim_id: int, status: ClaimStatus) -> bool:
    result = db.execute(
        update(Claim)
        .where(Claim.id == claim_id, Claim.status == ClaimStatus.PENDING)
        .values(status=status)
    )
    return result.rowcount == 1


def base_statement() -> Select[tuple[Claim]]:
    return select(Claim)
