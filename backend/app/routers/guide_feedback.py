from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DB, CurrentUser
from app.models.project import Project
from app.models.workflow import GuideFeedback
from app.models.user import UserRole
from app.schemas.workflow import GuideFeedbackOut, GuideFeedbackUpdateRequest
from app.utils.authz import ensure_participant
from app.utils.notify import notify

router = APIRouter(tags=["Guide Feedback"])


def _get_project_or_404(project_id: str, db: DB) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _to_out(f: GuideFeedback) -> GuideFeedbackOut:
    return GuideFeedbackOut(
        guideId=str(f.guide_id),
        guideName=f.guide_name,
        overallScore=f.overall_score,
        comment=f.comment,
        updatedAt=f.updated_at.isoformat(),
    )


@router.get("/projects/{project_id}/guide-feedback", response_model=GuideFeedbackOut | None)
def get_guide_feedback(project_id: str, current_user: CurrentUser, db: DB):
    """The guide's informal mark — explicitly not the official grade. Readable
    by the student, the assigned guide, the assigned reviewer (for context),
    and HOD. Returns null until the guide has given feedback at least once."""
    project = _get_project_or_404(project_id, db)
    ensure_participant(project, current_user)
    if not project.guide_feedback:
        return None
    return _to_out(project.guide_feedback)


@router.put("/projects/{project_id}/guide-feedback", response_model=GuideFeedbackOut)
def upsert_guide_feedback(project_id: str, payload: GuideFeedbackUpdateRequest, current_user: CurrentUser, db: DB):
    """Guide (must be the one assigned to this project) or HOD. Reviewer is
    deliberately excluded — the reviewer gives the official grade through
    the existing score-override + publish flow, not this one."""
    project = _get_project_or_404(project_id, db)
    is_assigned_guide = (
        current_user.role == UserRole.guide
        and project.assigned_guide_id == current_user.id
        and project.guide_submitted_at is not None
    )
    if not (is_assigned_guide or current_user.role == UserRole.hod):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project's assigned guide (or HOD) can give guide feedback.",
        )

    feedback = project.guide_feedback
    if feedback:
        feedback.overall_score = payload.overallScore
        feedback.comment = payload.comment
        feedback.updated_at = datetime.now(timezone.utc)
    else:
        feedback = GuideFeedback(
            project_id=project.id,
            guide_id=current_user.id,
            guide_name=current_user.name,
            overall_score=payload.overallScore,
            comment=payload.comment,
        )
        db.add(feedback)

    notify(db, project.student_id, "guide_feedback", f"Your guide shared feedback on \"{project.title}\"",
           body=payload.comment[:140], link=f"/student/discussion/{project.id}")

    db.commit()
    db.refresh(feedback)
    return _to_out(feedback)
