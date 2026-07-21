from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories import users


def delete_user(db: Session, current_user: User, user_id: int) -> None:
    target = users.get_by_id(db, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if target.id == current_user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Administrators cannot delete themselves")
    users.delete(db, target)
    db.commit()
