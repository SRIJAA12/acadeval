from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import DB, CurrentFacultyOrHOD
from app.models.project import Project, PipelineStatus
from app.models.evaluation import (
    EvaluationReport,
    InternalNote,
    ScoreOverrideHistory,
    FacultyEvaluation,
)
from app.schemas.report import (
    ScoreOverrideRequest,
    AddNoteRequest,
    FacultyReviewRequest,
)
router = APIRouter(tags=["Reviews"])


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/projects/{project_id}/scores", status_code=status.HTTP_200_OK)
def override_score(
    project_id: str,
    payload: ScoreOverrideRequest,
    current_user: CurrentFacultyOrHOD,
    db: DB,
):
    """Override a single dimension score and record in audit history."""
    project = _get_project_or_404(project_id, db)
    report = project.evaluation
    if not report:
        raise HTTPException(status_code=404, detail="Evaluation report not found")

    # Map dimension name to DB column
    dim_map = {
        "novelty": "novelty_score",
        "feasibility": "feasibility_score",
        "completeness": "completeness_score",
        "technicalDepth": "technical_depth_score",
        "clarity": "clarity_score",
        "similarityRisk": "similarity_risk_score",
        "publicationPotential": "publication_potential_score",
    }
    col = dim_map.get(payload.dimension)
    if not col:
        raise HTTPException(status_code=400, detail=f"Unknown dimension: {payload.dimension}")

    old_value = getattr(report, col) or 0

    # Record history
    hist = ScoreOverrideHistory(
        report_id=report.id,
        project_id=project.id,
        dimension=payload.dimension,
        old_value=old_value,
        new_value=payload.newValue,
        changed_by_id=current_user.id,
        changed_by_name=current_user.name,
        comment=payload.comment,
    )
    db.add(hist)

    # Apply override
    setattr(report, col, payload.newValue)

    # Recompute overall (simple average of non-null scores)
    score_cols = list(dim_map.values())
    non_null = [getattr(report, c) for c in score_cols if getattr(report, c) is not None]
    if non_null:
        report.overall_score = round(sum(non_null) / len(non_null), 1)
        os = report.overall_score
        report.grade = "A+" if os >= 90 else "A" if os >= 80 else "B" if os >= 70 else "C"

    db.commit()
    return {"message": "Score updated", "newOverall": report.overall_score}


@router.post("/projects/{project_id}/notes", status_code=status.HTTP_201_CREATED)
def add_note(
    project_id: str,
    payload: AddNoteRequest,
    current_user: CurrentFacultyOrHOD,
    db: DB,
):
    """Add an internal faculty note (never visible to students)."""
    project = _get_project_or_404(project_id, db)
    note = InternalNote(
        project_id=project.id,
        author_id=current_user.id,
        role=current_user.role.value,
        text=payload.text,
    )
    db.add(note)
    db.commit()
    return {"message": "Note added"}

@router.post("/projects/{project_id}/faculty-review", status_code=status.HTTP_201_CREATED)
def submit_faculty_review(
    project_id: str,
    payload: FacultyReviewRequest,
    current_user: CurrentFacultyOrHOD,
    db: DB,
):
    """Stores faculty review to validate AI evaluation."""

    project = _get_project_or_404(project_id, db)

    if not project.evaluation:
        raise HTTPException(
            status_code=404,
            detail="Evaluation report not found",
        )

    system_score = project.evaluation.novelty_score or 0.0

    review = FacultyEvaluation(
        project_id=project.id,
        evaluator_id=current_user.id,
        faculty_score=payload.faculty_score,
        system_score=system_score,
        score_delta=(payload.faculty_score * 10) - system_score,
        override_reason=payload.override_reason,
        is_confirmed=payload.is_confirmed,
    )

    db.add(review)
    db.commit()
    db.refresh(review)

    return {
        "message": "Faculty review submitted",
        "reviewId": str(review.id),
    }
@router.post("/projects/{project_id}/publish", status_code=status.HTTP_200_OK)
def publish_review(
    project_id: str,
    current_user: CurrentFacultyOrHOD,
    db: DB,
):
    """Publish the review — makes report visible to student as final (not preliminary)."""
    project = _get_project_or_404(project_id, db)

    project.pipeline_status = PipelineStatus.reviewed
    project.is_preliminary = False

    if project.evaluation:
        project.evaluation.published_at = datetime.now(timezone.utc)

    db.commit()

    # Module 14 — Email Notification to Student upon Review Publishing
    try:
        from app.services.notification_service import send_email
        student = project.student
        if student and student.email:
            score_val = project.evaluation.overall_score if project.evaluation else 0.0
            grade_val = project.evaluation.grade if project.evaluation else "N/A"
            subject = f"Faculty Review Published: {project.title}"
            body_html = f"""
                <p>Dear <strong>{student.name}</strong>,</p>
                <p>Prof. <strong>{current_user.name}</strong> has published the final review for your project <strong>"{project.title}"</strong>.</p>
                <div style="background:#f8fafc; border-left:4px solid #2a5298; padding:12px; margin:15px 0;">
                    <p style="margin:0;"><strong>Final Score:</strong> {score_val} / 10.0</p>
                    <p style="margin:5px 0 0 0;"><strong>Grade:</strong> {grade_val}</p>
                </div>
                <p>Log in to view the faculty feedback and notes.</p>
            """
            send_email(student.email, subject, body_html)
    except Exception as exc:
        pass

    return {"message": "Review published", "projectId": project_id}
