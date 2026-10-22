from fastapi import APIRouter, HTTPException

from app.dependencies import DB, CurrentUser
from app.models.project import Project
from app.models.workflow import DiscussionMessage
from app.models.user import UserRole
from app.schemas.workflow import DiscussionMessageOut, DiscussionPostRequest
from app.utils.authz import ensure_guide_student_participant
from app.utils.notify import notify

router = APIRouter(tags=["Discussion"])


def _get_project_or_404(project_id: str, db: DB) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _to_out(msg: DiscussionMessage, viewer_id: str) -> DiscussionMessageOut:
    return DiscussionMessageOut(
        messageId=str(msg.id),
        authorId=str(msg.author_id),
        authorName=msg.author_name,
        authorRole=msg.author_role,
        body=msg.body,
        createdAt=msg.created_at.isoformat(),
        unread=viewer_id not in (msg.read_by or []) and str(msg.author_id) != viewer_id,
    )


@router.get("/projects/{project_id}/discussion", response_model=list[DiscussionMessageOut])
def list_discussion(project_id: str, current_user: CurrentUser, db: DB):
    project = _get_project_or_404(project_id, db)
    ensure_guide_student_participant(project, current_user)
    return [_to_out(m, str(current_user.id)) for m in project.discussion_messages]


@router.post("/projects/{project_id}/discussion", response_model=DiscussionMessageOut, status_code=201)
def post_discussion_message(project_id: str, payload: DiscussionPostRequest, current_user: CurrentUser, db: DB):
    project = _get_project_or_404(project_id, db)
    ensure_guide_student_participant(project, current_user)

    msg = DiscussionMessage(
        project_id=project.id,
        author_id=current_user.id,
        author_name=current_user.name,
        author_role=current_user.role.value,
        body=payload.body,
        read_by=[str(current_user.id)],
    )
    db.add(msg)

    # Notify the other side of the conversation (guide <-> student only).
    recipients = set()
    if current_user.role == UserRole.student:
        recipient_link = f"/faculty/discussion/{project.id}"
        if project.assigned_guide_id and project.guide_submitted_at is not None:
            recipients.add(project.assigned_guide_id)
    else:
        recipient_link = f"/student/discussion/{project.id}"
        recipients.add(project.student_id)
    for recipient_id in recipients:
        notify(db, recipient_id, "discussion_message", f"New message on \"{project.title}\"",
               body=payload.body[:140], link=recipient_link)

    db.commit()
    db.refresh(msg)
    return _to_out(msg, str(current_user.id))


@router.post("/projects/{project_id}/discussion/read", status_code=204)
def mark_discussion_read(project_id: str, current_user: CurrentUser, db: DB):
    project = _get_project_or_404(project_id, db)
    ensure_guide_student_participant(project, current_user)
    uid = str(current_user.id)
    changed = False
    for msg in project.discussion_messages:
        if uid not in (msg.read_by or []):
            msg.read_by = [*(msg.read_by or []), uid]
            changed = True
    if changed:
        db.commit()
    return None
