from fastapi import HTTPException, status
from sqlalchemy import Select, or_, select

from app.models.claim import Claim
from app.models.user import User, UserRole


class ClaimAccessPolicy:
    def build_visibility_statement(self, current_user: User) -> Select[tuple[Claim]]:
        statement = select(Claim)
        if current_user.role == UserRole.ADMIN:
            return statement
        if current_user.role == UserRole.MANAGER:
            return statement.join(User, Claim.user_id == User.id).where(
                or_(Claim.user_id == current_user.id, User.manager_id == current_user.id)
            )
        return statement.where(Claim.user_id == current_user.id)

    def can_view_claim(self, current_user: User, claim: Claim) -> bool:
        if current_user.role == UserRole.ADMIN:
            return True
        if claim.user_id == current_user.id:
            return True
        return current_user.role == UserRole.MANAGER and claim.owner.manager_id == current_user.id

    def ensure_can_view_claim(self, current_user: User, claim: Claim) -> None:
        if not self.can_view_claim(current_user, claim):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted to view this claim")

    def ensure_can_change_status(self, current_user: User, claim: Claim) -> None:
        allowed = current_user.role == UserRole.ADMIN or (
            current_user.role == UserRole.MANAGER
            and claim.user_id != current_user.id
            and claim.owner.manager_id == current_user.id
        )
        if not allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted to update this claim")
