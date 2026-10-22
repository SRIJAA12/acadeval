from sqlalchemy.orm import Session

from app.models.workflow import Notification


def notify(
    db: Session,
    user_id,
    type: str,
    title: str,
    body: str = "",
    link: str | None = None,
) -> None:
    """Add an in-app notification. Caller commits. Best-effort — never raises
    on its own (the row construction can't fail), so callers can call this
    inline without wrapping every call site in try/except."""
    db.add(Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        link=link,
    ))
