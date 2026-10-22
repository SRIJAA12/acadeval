from fastapi import APIRouter, HTTPException

from app.dependencies import DB, CurrentHOD
from app.models.user import User, UserRole
from app.schemas.user import UserOut, UserRoleUpdate
from app.utils.audit import log_audit

router = APIRouter(tags=["Users"])


def _to_out(user: User) -> UserOut:
    return UserOut(
        userId=str(user.id),
        name=user.name,
        email=user.email,
        rollNo=user.roll_no,
        role=user.role,
        department=user.department,
        isActive=user.is_active,
        joinedAt=user.created_at.isoformat(),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(current_user: CurrentHOD, db: DB):
    """HOD: list all users in department."""
    users = db.query(User).order_by(User.created_at).all()
    return [_to_out(u) for u in users]


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(user_id: str, payload: UserRoleUpdate, current_user: CurrentHOD, db: DB):
    """HOD: change a user's role."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    old_role = user.role.value
    user.role = payload.role
    log_audit(db, current_user, "change_role", "user", str(user.id), {
        "from": old_role, "to": payload.role.value, "target_name": user.name,
    })
    db.commit()
    db.refresh(user)
    return _to_out(user)
