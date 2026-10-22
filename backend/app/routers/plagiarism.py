"""Plagiarism evidence endpoints. See app/services/plagiarism_checker.py for
how matches are generated. Reporting follows the methodology document's
wording guidance — "potential overlap found" / evidence shown, never
"plagiarism proven"; a human sets review_status."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DB, CurrentUser, CurrentFacultyOrHOD
from app.models.project import Project
from app.models.plagiarism import PlagiarismMatch, ReviewStatus
from app.models.user import User
from app.schemas.plagiarism import PlagiarismMatchOut, PlagiarismReportOut, ReviewDecisionRequest
from app.utils.authz import ensure_participant
from app.utils.audit import log_audit

router = APIRouter(tags=["Plagiarism"])


def _get_project_or_404(project_id: str, db) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _match_to_out(db, m: PlagiarismMatch) -> PlagiarismMatchOut:
    reviewer = db.query(User).filter(User.id == m.reviewed_by_id).first() if m.reviewed_by_id else None
    return PlagiarismMatchOut(
        matchId=str(m.id), matchType=m.match_type.value,
        sourceProjectId=str(m.source_project_id) if m.source_project_id else None,
        sourceLabel=m.source_label,
        candidatePassage=m.candidate_passage, candidateLocation=m.candidate_location,
        sourcePassage=m.source_passage, sourceLocation=m.source_location,
        score=round(m.score, 4), reviewStatus=m.review_status.value,
        reviewedByName=reviewer.name if reviewer else None,
        reviewedAt=m.reviewed_at.isoformat() if m.reviewed_at else None,
        reviewerComment=m.reviewer_comment,
        createdAt=m.created_at.isoformat(),
    )


def _summary_text(matches: list[PlagiarismMatch]) -> str:
    if not matches:
        return (
            "No significant match was found in the sources searched (other submitted AcadEval+ "
            "projects and linked GitHub repositories). This does not prove the submission is "
            "original; the source may be outside the available corpus or the wording may have "
            "been substantially changed."
        )
    best = max(matches, key=lambda m: m.score)
    return (
        f"Potential overlap found: {len(matches)} passage(s)/section(s) matched records in the "
        f"AcadEval+ corpus. The highest similarity was {best.score:.2f} against \"{best.source_label}\". "
        "This is a similarity finding, not an automatic determination of misconduct — a faculty "
        "reviewer decides whether the overlap is improper."
    )


@router.get("/projects/{project_id}/plagiarism-report", response_model=PlagiarismReportOut)
def get_plagiarism_report(project_id: str, current_user: CurrentUser, db: DB):
    """Full evidence (source project, matched passage, score) shown to the
    student as well as guide/reviewer/HOD. Gated the same way as the rest of
    the report — a guide only sees this once the student has submitted to
    them (see app/utils/authz.py)."""
    project = _get_project_or_404(project_id, db)
    ensure_participant(project, current_user)

    matches = (
        db.query(PlagiarismMatch)
        .filter(PlagiarismMatch.project_id == project_id)
        .order_by(PlagiarismMatch.score.desc())
        .all()
    )
    text_matches = [m for m in matches if m.match_type.value == "text"]
    code_matches = [m for m in matches if m.match_type.value == "code"]

    from app.models.plagiarism import CodeFingerprint
    fp = db.query(CodeFingerprint).filter(CodeFingerprint.project_id == project_id).first()

    return PlagiarismReportOut(
        projectId=project_id,
        textMax=round(max((m.score for m in text_matches), default=0.0), 4),
        codeMax=round(max((m.score for m in code_matches), default=0.0), 4),
        textMatchCount=len(text_matches),
        codeMatchCount=len(code_matches),
        codeFetchError=fp.fetch_error if fp else None,
        matches=[_match_to_out(db, m) for m in matches],
        summaryText=_summary_text(matches),
    )


@router.patch("/plagiarism-matches/{match_id}/review", response_model=PlagiarismMatchOut)
def review_plagiarism_match(match_id: str, payload: ReviewDecisionRequest, current_user: CurrentFacultyOrHOD, db: DB):
    """Guide/reviewer/HOD only — sets the human review decision for one piece
    of evidence. Use human review for adverse academic-integrity decisions."""
    match = db.query(PlagiarismMatch).filter(PlagiarismMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Plagiarism match not found")

    valid = {s.value for s in ReviewStatus} - {"unreviewed"}
    if payload.reviewStatus not in valid:
        raise HTTPException(status_code=422, detail=f"reviewStatus must be one of: {', '.join(sorted(valid))}")

    project = _get_project_or_404(str(match.project_id), db)
    ensure_participant(project, current_user)

    match.review_status = ReviewStatus(payload.reviewStatus)
    match.reviewer_comment = payload.reviewerComment
    match.reviewed_by_id = current_user.id
    match.reviewed_at = datetime.now(timezone.utc)

    log_audit(db, current_user, "review_plagiarism_match", "plagiarism_match", str(match.id), {
        "reviewStatus": payload.reviewStatus,
    })
    db.commit()
    db.refresh(match)
    return _match_to_out(db, match)
