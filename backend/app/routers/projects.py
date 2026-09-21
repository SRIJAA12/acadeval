"""
Projects router — Module 11 edition
=====================================
"""

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status

from app.dependencies import DB, CurrentUser, CurrentStudent, CurrentFaculty, CurrentFacultyOrHOD
from app.models.project import Project, ProjectFile, PipelineStatus, SubmissionType
from app.schemas.project import (
    ProjectSummary, ProjectStatusResponse, UploadResponse,
    BatchUploadResponse, BatchJobStatusResponse,
)
from app.utils.files import (
    DOCUMENT_EXTENSIONS,
    VIDEO_EXTENSIONS,
    get_file_type,
    save_upload_file,
    validate_upload_file,
)

log = logging.getLogger(__name__)

router = APIRouter(tags=["Projects"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_summary(project: Project) -> ProjectSummary:
    score = project.evaluation.overall_score if project.evaluation else None
    return ProjectSummary(
        projectId=str(project.id),
        studentName=project.student.name,
        rollNo=project.student.roll_no or "",
        title=project.title,
        submissionType=project.submission_type,
        domain=project.domain,
        submittedOn=project.submitted_on.date().isoformat(),
        pipelineStatus=project.pipeline_status,
        overallScore=score,
    )


def _try_enqueue(project_id: str) -> str | None:
    """Enqueue the Celery pipeline and return the chain root task id, or None if Redis is down."""
    try:
        from app.tasks.pipeline import enqueue_pipeline
        result = enqueue_pipeline(project_id)
        return result.id
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Celery enqueue failed for %s (%s) — falling back to BackgroundTasks", project_id, exc
        )
        return None


def _fallback_background_pipeline(project_id: uuid.UUID):
    """
    Synchronous fallback used only when Redis / Celery is unreachable.
    Runs the full pipeline in-process (blocks the background thread but
    keeps the app functional without Celery).
    """
    from pathlib import Path
    from app.database import SessionLocal
    from app.services.document_parser import document_parser_service
    from app.services.classifier import classifier_service
    from app.services.extractor import extractor_service
    import logging

    log = logging.getLogger(__name__)
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        project.pipeline_status = PipelineStatus.ai_processing
        db.commit()

        # Document parsing
        extracted_text, parsed_title, parsed_abstract = "", "", ""
        for pf in project.files:
            if pf.storage_path and Path(pf.storage_path).exists():
                try:
                    parsed = document_parser_service.parse_uploaded_file(
                        file_path=pf.storage_path, filename=pf.original_filename
                    )
                    struct = parsed.get("parsed_structure", {})
                    if struct.get("title") and not parsed_title:
                        parsed_title = struct["title"]
                    if struct.get("abstract"):
                        parsed_abstract += "\n" + struct["abstract"]
                    extracted_text += "\n" + parsed.get("raw_text", "")
                except Exception as exc:
                    log.warning("File parse failed (%s): %s", pf.original_filename, exc)

        if project.github_url:
            try:
                gh = document_parser_service.fetch_github_features(project.github_url)
                extracted_text += "\n" + gh.get("raw_text", "")
            except Exception:
                pass

        if parsed_title and (not project.title or "Uploaded Project" in project.title):
            project.title = parsed_title

        effective_abstract = (
            project.abstract or parsed_abstract or extracted_text[:2000] or project.title
        ).strip()
        project.abstract = effective_abstract
        project.parsed_text = extracted_text.strip() or None

        # Module 1: classify
        sub_domain = "General"
        try:
            cls = classifier_service.classify_project(project.title, effective_abstract)
            if cls.get("domain"):
                project.domain = cls["domain"]
            sub_domain = cls.get("sub_domain") or sub_domain
        except Exception as exc:
            log.warning("Classification skipped: %s", exc)

        # Module 2: entity extraction (pass full extracted file text so presentation slide text is extracted)
        try:
            full_proposal_text = f"{project.title}\n{effective_abstract}\n{extracted_text}"
            entities = extractor_service.extract_entities(full_proposal_text)
            entities["sub_domain"] = sub_domain
            project.extracted_entities = entities
        except Exception as exc:
            log.warning("Entity extraction skipped: %s", exc)
            entities = {}

        db.commit()

        # Preserve the same no-leakage order as the Celery chain: score against
        # historical projects first, then make this candidate historical data.
        # Any dependency failure remains visible; no placeholder is emitted.
        from app.tasks.pipeline import task_score_and_report, task_ingest_graph, task_finalise
        task_score_and_report.run(str(project.id))
        task_ingest_graph.run(str(project.id))
        task_finalise.run(str(project.id))
        log.info("Fallback pipeline complete for %s", project_id)
    except Exception as exc:
        log.exception("Fallback pipeline failed for %s: %s", project_id, exc)
    finally:
        db.close()


# ── Read endpoints ─────────────────────────────────────────────────────────────

@router.get("/projects/my", response_model=List[ProjectSummary])
def get_my_projects(current_user: CurrentStudent, db: DB):
    """Student: list own submissions."""
    projects = (
        db.query(Project)
        .filter(Project.student_id == current_user.id)
        .order_by(Project.submitted_on.desc())
        .all()
    )
    return [_to_summary(p) for p in projects]


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: str, current_user: CurrentStudent, db: DB):
    """Student: delete an owned submitted project."""
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.student_id == current_user.id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found or access denied")
    
    # Delete associated files, evaluations, appeals, and graph shadow nodes
    if project.evaluation:
        db.delete(project.evaluation)
    for f in project.files:
        db.delete(f)
    db.delete(project)
    db.commit()
    return None


@router.get("/projects", response_model=List[ProjectSummary])
def get_all_projects(current_user: CurrentFacultyOrHOD, db: DB):
    """Phase 1: All Guide/Reviewer/HOD see all submitted projects."""
    projects = db.query(Project).order_by(Project.submitted_on.desc()).all()
    return [_to_summary(p) for p in projects]


@router.get("/projects/{project_id}/status", response_model=ProjectStatusResponse)
def get_project_status(project_id: str, current_user: CurrentUser, db: DB):
    """Legacy status endpoint — returns DB pipeline_status."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectStatusResponse(status=project.pipeline_status.value)


@router.get("/projects/{project_id}/pipeline-status")
def get_pipeline_status(project_id: str, current_user: CurrentUser, db: DB):
    """
    Module 11 — Rich async status endpoint.
    Merges the DB pipeline_status with the Celery task state so the frontend
    can show a live progress bar without a WebSocket.

    Response shape:
      {
        "project_id": "...",
        "db_status": "ai_processing",
        "celery_state": "STARTED" | "SUCCESS" | "FAILURE" | "PENDING" | null,
        "celery_task_id": "..." | null,
        "ready": true | false,
        "error": "..." | null
      }
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    celery_task_id = getattr(project, "celery_task_id", None)
    celery_state = None
    error_msg = None

    if celery_task_id:
        try:
            from app.worker import celery_app
            from celery.result import AsyncResult
            ar = AsyncResult(celery_task_id, app=celery_app)
            celery_state = ar.state
            if ar.failed():
                error_msg = str(ar.result)
        except Exception:
            celery_state = "UNKNOWN"

    ready = project.pipeline_status in (
        PipelineStatus.awaiting_review,
        PipelineStatus.reviewed,
    )

    return {
        "project_id": project_id,
        "db_status": project.pipeline_status.value,
        "celery_state": celery_state,
        "celery_task_id": celery_task_id,
        "ready": ready,
        "error": error_msg,
    }


# ── Upload endpoint (Module 11 — Celery version) ──────────────────────────────

@router.post("/projects/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_project(
    current_user: CurrentStudent,
    db: DB,
    mode: str = Form(...),
    domain: str = Form(...),
    title: Optional[str] = Form(None),
    teamMembers: Optional[str] = Form(None),
    abstract: Optional[str] = Form(None),
    githubUrl: Optional[str] = Form(None),
    relatedSubmissionId: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
):
    """
    Upload a project file/URL.  The response is returned immediately (<200 ms).
    The AI pipeline (parse → classify → extract → graph → score → report)
    runs asynchronously in a Celery worker and the frontend polls
    GET /projects/{project_id}/pipeline-status until ready=true.
    """
    try:
        submission_type = SubmissionType(mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="mode must be document, video, or abstract") from exc

    if submission_type == SubmissionType.abstract:
        word_count = len((abstract or "").split())
        if word_count < 150 or word_count > 500:
            raise HTTPException(status_code=422, detail="Abstract submissions must contain 150–500 words")
        if files:
            raise HTTPException(status_code=422, detail="Abstract submissions must not include files")
    elif submission_type == SubmissionType.document:
        if not files:
            raise HTTPException(status_code=422, detail="Document submissions require at least one file")
        for upload_file in files:
            validate_upload_file(upload_file, DOCUMENT_EXTENSIONS)
    else:
        if not files:
            raise HTTPException(status_code=422, detail="Video submissions require an MP4 or MOV file")
        extensions = [validate_upload_file(upload_file, VIDEO_EXTENSIONS | {"pptx"}) for upload_file in files]
        if not any(extension in VIDEO_EXTENSIONS for extension in extensions):
            raise HTTPException(status_code=422, detail="Video submissions require an MP4 or MOV file")

    related_submission_id = None
    if relatedSubmissionId:
        try:
            related_submission_id = uuid.UUID(relatedSubmissionId)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="relatedSubmissionId must be a valid UUID") from exc

    effective_title = title
    if not effective_title and files:
        effective_title = files[0].filename or "Uploaded Project"
    if not effective_title:
        effective_title = f"{domain} Project"

    project = Project(
        student_id=current_user.id,
        title=effective_title,
        domain=domain,
        submission_type=submission_type,
        github_url=githubUrl,
        team_members=teamMembers,
        abstract=abstract,
        related_submission_id=related_submission_id,
        pipeline_status=PipelineStatus.uploaded,
        assigned_guide_id=None,
    )
    db.add(project)
    db.flush()  # get project.id before saving files

    for upload_file in files:
        if upload_file.filename:
            storage_path = await save_upload_file(upload_file, str(project.id))
            db.add(ProjectFile(
                project_id=project.id,
                file_type=get_file_type(upload_file.filename),
                original_filename=upload_file.filename,
                storage_path=storage_path,
            ))

    db.commit()
    db.refresh(project)

    project_id_str = str(project.id)

    # ── Enqueue Celery pipeline ────────────────────────────────────────────────
    job_id = _try_enqueue(project_id_str)

    if job_id:
        # Store the chain root task id on the project so /pipeline-status can poll it
        if hasattr(project, "celery_task_id"):
            project.celery_task_id = job_id
            db.commit()
    else:
        # Redis unavailable — run synchronously in a thread (graceful degradation)
        import threading
        t = threading.Thread(
            target=_fallback_background_pipeline,
            args=(project.id,),
            daemon=True,
        )
        t.start()

    return UploadResponse(projectId=project_id_str)


# ── Batch upload ───────────────────────────────────────────────────────────────

@router.post("/projects/batch", response_model=BatchUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def batch_upload(
    current_user: CurrentFaculty,
    db: DB,
    files: List[UploadFile] = File(...),
):
    """
    Batch upload: each file becomes an independent project that is immediately
    enqueued as a separate Celery pipeline chain.
    Returns a batchId and the list of created project IDs.
    """
    log = logging.getLogger(__name__)

    if not 1 <= len(files) <= 60:
        raise HTTPException(status_code=422, detail="Batch upload accepts between 1 and 60 files")
    for upload_file in files:
        validate_upload_file(upload_file, DOCUMENT_EXTENSIONS)

    batch_id = str(uuid.uuid4())
    project_ids: list[str] = []

    # Find or create a placeholder student for batch uploads (faculty uploads on behalf)
    # Use the faculty user themselves as the student for batch context
    for upload_file in files:
        if not upload_file.filename:
            continue

        project = Project(
            student_id=current_user.id,
            title=upload_file.filename,
            domain="Unclassified",
            submission_type=SubmissionType.document,
            pipeline_status=PipelineStatus.uploaded,
            batch_id=batch_id,
        )
        db.add(project)
        db.flush()

        storage_path = await save_upload_file(upload_file, str(project.id))
        db.add(ProjectFile(
            project_id=project.id,
            file_type=get_file_type(upload_file.filename),
            original_filename=upload_file.filename,
            storage_path=storage_path,
        ))
        db.commit()
        db.refresh(project)

        pid = str(project.id)
        project_ids.append(pid)

        job_id = _try_enqueue(pid)
        if job_id and hasattr(project, "celery_task_id"):
            project.celery_task_id = job_id
            db.commit()
        elif not job_id:
            import threading
            threading.Thread(
                target=_fallback_background_pipeline,
                args=(project.id,),
                daemon=True,
            ).start()

        log.info("Batch %s — enqueued project %s (job %s)", batch_id, pid, job_id)

    return BatchUploadResponse(batchId=batch_id, totalFiles=len(project_ids), projectIds=project_ids)


@router.get("/projects/batch/{batch_id}/status", response_model=BatchJobStatusResponse)
def get_batch_status(batch_id: str, current_user: CurrentFacultyOrHOD, db: DB):
    """Return live, persistent progress for every project created in a batch."""
    projects = (
        db.query(Project)
        .filter(Project.batch_id == batch_id)
        .order_by(Project.submitted_on)
        .all()
    )
    if not projects:
        raise HTTPException(status_code=404, detail="Batch not found")

    processed = sum(
        project.pipeline_status in (PipelineStatus.awaiting_review, PipelineStatus.reviewed)
        for project in projects
    )
    failed = 0
    for project in projects:
        if not project.celery_task_id:
            continue
        try:
            from celery.result import AsyncResult
            from app.worker import celery_app
            if AsyncResult(project.celery_task_id, app=celery_app).failed():
                failed += 1
        except Exception:
            continue

    total = len(projects)
    terminal = processed + failed
    batch_status = "completed" if terminal == total and failed == 0 else ("failed" if terminal == total else "processing")
    completed_at = max(project.updated_at for project in projects).isoformat() if terminal == total else None

    return BatchJobStatusResponse(
        batchId=batch_id,
        totalFiles=total,
        processed=processed,
        failed=failed,
        status=batch_status,
        startedAt=min(project.submitted_on for project in projects).isoformat(),
        completedAt=completed_at,
        projects=[_to_summary(project) for project in projects],
    )
