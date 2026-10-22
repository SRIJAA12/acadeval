from sqlalchemy.orm import Session

from app.models.user import User
from app.models.workflow import AuditLog


def log_audit(
    db: Session,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: str,
    details: dict | None = None,
) -> None:
    """Record an audit entry. Caller is responsible for db.commit(); this
    only adds to the session so it can be committed atomically with the
    action it's logging."""
    db.add(AuditLog(
        actor_id=actor.id if actor else None,
        actor_name=actor.name if actor else "system",
        actor_role=actor.role.value if actor else "system",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details or {},
    ))
