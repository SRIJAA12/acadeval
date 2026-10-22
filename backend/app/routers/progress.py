import os
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Form, File, UploadFile

from app.config import settings
from app.dependencies import DB, CurrentUser
from app.models.project import Project
from app.models.workflow import ProgressUpdate
from app.models.user import UserRole
from app.schemas.workflow import ProgressUpdateOut
from app.utils.authz import ensure_participant
from app.utils.files import DOCUMENT_EXTENSIONS, validate_upload_file, get_upload_path
from app.utils.notify import notify

router = APIRouter(tags=["Progress"])


def _get_project_or_404(project_id: str, db: DB) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _save_progress_attachment(upload_file: UploadFile, project_id: str) -> str:
    """Same validation/size-limit contract as save_upload_file, but scoped to
    docs/ppts only (no video) — a progress update attaches supporting
    material, not a resubmission."""
    validate_upload_file(upload_file, DOCUMENT_EXTENSIONS)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    dest_path = get_upload_path(project_id, upload_file.filename or "attachment")

    size = 0
    with open(dest_path, "wb") as buffer:
        while chunk := await upload_file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                buffer.close()
                os.unlink(dest_path)
                raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")
            buffer.write(chunk)
    return str(dest_path)


def _to_out(p: ProgressUpdate) -> ProgressUpdateOut:
    return ProgressUpdateOut(
        updateId=str(p.id),
        authorId=str(p.author_id),
        authorName=p.author_name,
        content=p.content,
        attachmentFilename=p.attachment_filename,
        githubUrl=p.github_url,
        createdAt=p.created_at.isoformat(),
    )


@router.get("/projects/{project_id}/progress", response_model=list[ProgressUpdateOut])
def list_progress(project_id: str, current_user: CurrentUser, db: DB):
    """Newest first — the student's latest update is what guide/reviewer/HOD
    see at the top. Visible to the student, assigned guide, assigned
    reviewer (they need evidence for the official grade too), and HOD."""
    project = _get_project_or_404(project_id, db)
    ensure_participant(project, current_user)
    return [_to_out(p) for p in project.progress_updates]


@router.get("/projects/{project_id}/progress/{update_id}/attachment")
def download_progress_attachment(project_id: str, update_id: str, current_user: CurrentUser, db: DB):
    from fastapi.responses import FileResponse

    project = _get_project_or_404(project_id, db)
    ensure_participant(project, current_user)
    update = db.query(ProgressUpdate).filter(ProgressUpdate.id == update_id, ProgressUpdate.project_id == project_id).first()
    if not update or not update.attachment_path:
        raise HTTPException(status_code=404, detail="No attachment on this update")
    return FileResponse(update.attachment_path, filename=update.attachment_filename or "attachment")


@router.post("/projects/{project_id}/progress", response_model=ProgressUpdateOut, status_code=status.HTTP_201_CREATED)
async def post_progress(
    project_id: str,
    current_user: CurrentUser,
    db: DB,
    content: str = Form(...),
    githubUrl: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Student only. Append-only — never edits or deletes a prior entry, so
    the project's progress history is never lost, only added to. An
    attachment (doc/ppt) and/or an updated GitHub link are both optional
    additions to the required text note."""
    project = _get_project_or_404(project_id, db)
    if current_user.role != UserRole.student or project.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project's own student can post a progress update")

    attachment_path = None
    attachment_filename = None
    if file and file.filename:
        attachment_path = await _save_progress_attachment(file, project_id)
        attachment_filename = file.filename

    update = ProgressUpdate(
        project_id=project.id,
        author_id=current_user.id,
        author_name=current_user.name,
        content=content,
        attachment_path=attachment_path,
        attachment_filename=attachment_filename,
        github_url=githubUrl or None,
    )
    db.add(update)

    recipients = []
    if project.assigned_guide_id and project.guide_submitted_at is not None:
        recipients.append(project.assigned_guide_id)
    if project.assigned_reviewer_id:
        recipients.append(project.assigned_reviewer_id)
    for recipient_id in recipients:
        notify(db, recipient_id, "progress_update", f"New progress update on \"{project.title}\"",
               body=content[:140], link=f"/faculty/discussion/{project.id}")

    db.commit()
    db.refresh(update)
    return _to_out(update)
