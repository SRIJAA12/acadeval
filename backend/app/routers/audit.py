from app.dependencies import DB, CurrentHOD
from app.models.workflow import AuditLog
from app.schemas.workflow import AuditLogOut
from fastapi import APIRouter

router = APIRouter(tags=["Audit"])


def _to_out(a: AuditLog) -> AuditLogOut:
    return AuditLogOut(
        auditLogId=str(a.id),
        actorName=a.actor_name,
        actorRole=a.actor_role,
        action=a.action,
        entityType=a.entity_type,
        entityId=a.entity_id,
        details=a.details or {},
        createdAt=a.created_at.isoformat(),
    )


@router.get("/audit-logs", response_model=list[AuditLogOut])
def list_audit_logs(current_user: CurrentHOD, db: DB, limit: int = 100):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()
    return [_to_out(a) for a in rows]
