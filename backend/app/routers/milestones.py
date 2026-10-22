from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DB, CurrentUser
from app.models.project import Project
from app.models.workflow import Milestone, MilestoneStatus
from app.models.user import UserRole
from app.schemas.workflow import MilestoneOut, MilestoneSubmitRequest, MilestoneReviewRequest
from app.utils.authz import ensure_participant, ensure_assigned
from app.utils.notify import notify

router = APIRouter(tags=["Milestones"])


def _to_out(m: Milestone) -> MilestoneOut:
    return MilestoneOut(
        milestoneId=str(m.id),
        orderIndex=m.order_index,
        title=m.title,
        description=m.description,
        status=m.status.value,
        studentSubmission=m.student_submission,
        guideComment=m.guide_comment,
        submittedAt=m.submitted_at.isoformat() if m.submitted_at else None,
        reviewedAt=m.reviewed_at.isoformat() if m.reviewed_at else None,
    )


def _get_project_or_404(project_id: str, db: DB) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneOut])
def list_milestones(project_id: str, current_user: CurrentUser, db: DB):
    project = _get_project_or_404(project_id, db)
    ensure_participant(project, current_user)
    return [_to_out(m) for m in project.milestones]


@router.patch("/milestones/{milestone_id}/submit", response_model=MilestoneOut)
def submit_milestone(milestone_id: str, payload: MilestoneSubmitRequest, current_user: CurrentUser, db: DB):
    """Student: submit progress notes for one of their project's milestones."""
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    project = milestone.project
    if current_user.role != UserRole.student or project.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project's own student can submit")

    milestone.student_submission = payload.text
    milestone.status = MilestoneStatus.submitted
    milestone.submitted_at = datetime.now(timezone.utc)
    milestone.guide_comment = None
    db.commit()
    db.refresh(milestone)

    if project.assigned_guide_id:
        notify(db, project.assigned_guide_id, "milestone_submitted",
               f"{current_user.name} submitted \"{milestone.title}\" for {project.title}",
               link=f"/faculty/report/{project.id}")
        db.commit()

    return _to_out(milestone)


@router.patch("/milestones/{milestone_id}/review", response_model=MilestoneOut)
def review_milestone(milestone_id: str, payload: MilestoneReviewRequest, current_user: CurrentUser, db: DB):
    """Guide (or HOD): approve a submitted milestone or request revision."""
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    project = milestone.project
    if current_user.role not in (UserRole.guide, UserRole.hod):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only a guide or HOD can review milestones")
    ensure_assigned(project, current_user)

    milestone.status = MilestoneStatus.approved if payload.approve else MilestoneStatus.revision_requested
    milestone.guide_comment = payload.comment
    milestone.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(milestone)

    notify(
        db, project.student_id, "milestone_reviewed",
        f"\"{milestone.title}\" was {'approved' if payload.approve else 'sent back for revision'}",
        body=payload.comment or "",
        link=f"/student/report/{project.id}",
    )
    db.commit()

    return _to_out(milestone)
