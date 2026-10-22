from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, UserRole
from app.utils.auth import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(*roles: UserRole):
    """
    FastAPI dependency factory: require_role("hod") or require_role("guide", "reviewer").
    Usage:  CurrentUser = Depends(require_role("hod"))
    """
    def _checker(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {[r.value for r in roles]}",
            )
        return current_user
    return _checker


# Convenience typed dependency aliases
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentStudent = Annotated[User, Depends(require_role(UserRole.student))]
CurrentFaculty = Annotated[User, Depends(require_role(UserRole.guide, UserRole.reviewer))]
CurrentFacultyOrHOD = Annotated[User, Depends(require_role(UserRole.guide, UserRole.reviewer, UserRole.hod))]
# The reviewer gives the official grade; the guide's own marks are informal
# (see app/routers/guide_feedback.py) and never touch the official record.
CurrentReviewerOrHOD = Annotated[User, Depends(require_role(UserRole.reviewer, UserRole.hod))]
CurrentHOD = Annotated[User, Depends(require_role(UserRole.hod))]
CurrentCoordinator = Annotated[User, Depends(require_role(UserRole.coordinator))]
CurrentCoordinatorOrHOD = Annotated[User, Depends(require_role(UserRole.coordinator, UserRole.hod))]
CurrentFacultyOrHODOrCoordinator = Annotated[
    User, Depends(require_role(UserRole.guide, UserRole.reviewer, UserRole.hod, UserRole.coordinator))
]
DB = Annotated[Session, Depends(get_db)]
