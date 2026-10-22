from fastapi import APIRouter, HTTPException

from app.dependencies import DB, CurrentUser
from app.models.workflow import Notification
from app.schemas.workflow import NotificationOut

router = APIRouter(tags=["Notifications"])


def _to_out(n: Notification) -> NotificationOut:
    return NotificationOut(
        notificationId=str(n.id),
        type=n.type,
        title=n.title,
        body=n.body,
        link=n.link,
        isRead=n.is_read,
        createdAt=n.created_at.isoformat(),
    )


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(current_user: CurrentUser, db: DB, limit: int = 30):
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return [_to_out(n) for n in rows]


@router.get("/notifications/unread-count")
def unread_count(current_user: CurrentUser, db: DB):
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .count()
    )
    return {"count": count}


@router.patch("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: str, current_user: CurrentUser, db: DB):
    n = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == current_user.id
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    db.refresh(n)
    return _to_out(n)


@router.post("/notifications/read-all", status_code=204)
def mark_all_read(current_user: CurrentUser, db: DB):
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
    return None
