from typing import List
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import DB, CurrentUser, CurrentFacultyOrHOD
from app.models.project import Project
from app.models.evaluation import EvaluationReport
from app.models.user import UserRole
from app.schemas.report import PublicEvaluationReport, InternalEvaluationReport, DimensionScores

router = APIRouter(tags=["Reports"])


def _empty_dimension_scores(is_abstract: bool) -> DimensionScores:
    return DimensionScores(
        novelty=0,
        feasibility=0,
        completeness=None if is_abstract else 0,
        technicalDepth=0,
        clarity=0,
        similarityRisk=0,
        publicationPotential=0,
    )


def _report_to_public(project: Project, report: EvaluationReport) -> PublicEvaluationReport:
    from app.schemas.report import SimilarityInfo, WritingQuality, CitationInfo, ImprovementWeek
    is_abstract = project.submission_type.value == "abstract"
    scores = DimensionScores(
        novelty=report.novelty_score,
        feasibility=report.feasibility_score,
        completeness=None if is_abstract else report.completeness_score,
        technicalDepth=report.technical_depth_score,
        clarity=report.clarity_score,
        similarityRisk=report.similarity_risk_score,
        publicationPotential=report.publication_potential_score,
    )
    roadmap = [
        ImprovementWeek(week=w.get("week", idx + 1), focus=w.get("focus", "Task"), actions=w.get("actions", []))
        for idx, w in enumerate(report.improvement_roadmap or [])
        if isinstance(w, dict)
    ]

    wq = None
    if report.writing_quality and isinstance(report.writing_quality, dict):
        raw_wq = report.writing_quality
        readability = raw_wq.get("readability", raw_wq.get("metrics", {}).get("readability", 0.0))
        passive_count = raw_wq.get("passiveVoiceCount", raw_wq.get("metrics", {}).get("passive_voice_count", 0))
        tone_flags = raw_wq.get("toneFlags") or raw_wq.get("flags") or []
        wq = WritingQuality(
            readability=float(readability),
            passiveVoiceCount=int(passive_count),
            toneFlags=[str(f) for f in tone_flags],
        )

    cit = None
    if report.citations and isinstance(report.citations, dict):
        raw_cit = report.citations
        ieee = raw_cit.get("ieeeCompliancePercent", raw_cit.get("summary", {}).get("ieee_compliance_percent", 0.0))
        missing = raw_cit.get("missingReferences") or raw_cit.get("flags") or []
        cit = CitationInfo(
            ieeeCompliancePercent=float(ieee),
            missingReferences=[str(m) for m in missing],
        )

    return PublicEvaluationReport(
        projectId=str(project.id),
        title=project.title,
        domain=project.domain or "General CSE",
        submissionType=project.submission_type,
        pipelineStatus=project.pipeline_status,
        isPreliminary=bool(project.is_preliminary),
        overallScore=report.overall_score if report.overall_score is not None else 0.0,
        grade=report.grade or "N/A",
        dimensionScores=scores,
        missingSections=report.missing_sections or [],
        similarity=SimilarityInfo(
            internalScore=report.similarity_internal or 0.0,
            externalScore=report.similarity_external or 0.0,
            isDuplicate=bool(report.is_duplicate),
        ),
        feasibilityRating=report.feasibility_rating or "Pending",
        noveltyVerdict=report.novelty_verdict or "Pending",
        writingQuality=wq,
        citations=cit,
        strengths=report.strengths or [],
        weaknesses=report.weaknesses or [],
        improvementRoadmap=roadmap,
        badges=report.badges or [],
        percentileRanks=report.percentile_ranks or {},
    )


def _report_to_internal(
    project: Project, report: EvaluationReport
) -> InternalEvaluationReport:
    from app.schemas.report import FacultyNote, ExplainabilityAnnotation, ScoreOverrideEntry
    public = _report_to_public(project, report)

    notes = [
        FacultyNote(
            author=getattr(n, "author_user", None).name if getattr(n, "author_user", None) else "Faculty",
            role=n.role or "guide",
            text=n.text or "",
            timestamp=n.timestamp.isoformat() if hasattr(n, "timestamp") and n.timestamp else "",
        )
        for n in (project.notes or [])
    ]

    overrides = [
        ScoreOverrideEntry(
            dimension=o.dimension,
            oldValue=o.old_value,
            newValue=o.new_value,
            by=o.changed_by_name,
            comment=o.comment,
            timestamp=o.timestamp.isoformat() if hasattr(o, "timestamp") and o.timestamp else "",
        )
        for o in (report.score_overrides or [])
        if hasattr(o, "dimension")
    ]

    annotations = [
        ExplainabilityAnnotation(
            sentence=a.get("sentence", ""),
            weight=float(a.get("weight", 0.0)),
            reason=a.get("reason", "")
        )
        for a in (report.explainability_annotations or [])
        if isinstance(a, dict)
    ]

    return InternalEvaluationReport(
        **public.model_dump(),
        facultyNotes=notes,
        explainabilityAnnotations=annotations,
        flaggingReasons=report.flagging_reasons or [],
        assignedGuide=project.guide.name if getattr(project, "guide", None) else "Guide Unassigned",
        assignedReviewer=project.reviewer.name if getattr(project, "reviewer", None) else None,
        scoreOverrideHistory=overrides,
    )


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_or_create_report(project: Project, db: Session) -> EvaluationReport:
    """Return the report or an unsaved pending view; GET requests stay read-only."""
    if project.evaluation:
        return project.evaluation

    return EvaluationReport(
        project_id=project.id,
        overall_score=0.0,
        grade="N/A",
        novelty_score=None,
        feasibility_score=None,
        completeness_score=None,
        technical_depth_score=None,
        clarity_score=None,
        similarity_risk_score=None,
        publication_potential_score=None,
        feasibility_rating="Pending",
        novelty_verdict="Pending",
        strengths=[],
        weaknesses=[],
        improvement_roadmap=[],
        badges=[],
        percentile_ranks={},
        flagging_reasons=[],
        explainability_annotations=[],
    )


@router.get("/projects/my/reports", response_model=List[PublicEvaluationReport])
def get_my_reports(current_user: CurrentUser, db: DB):
    """Student: list evaluation reports for all own submissions."""
    projects = (
        db.query(Project)
        .filter(Project.student_id == current_user.id)
        .order_by(Project.submitted_on.desc())
        .all()
    )
    reports = []
    for p in projects:
        rep = _get_or_create_report(p, db)
        reports.append(_report_to_public(p, rep))
    return reports


@router.get("/projects/{project_id}/report/public", response_model=PublicEvaluationReport)
def get_public_report(project_id: str, current_user: CurrentUser, db: DB):
    """Student-safe report — never includes internal fields."""
    project = _get_project_or_404(project_id, db)

    # Students can only read their own reports
    if current_user.role == UserRole.student and project.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    report = _get_or_create_report(project, db)
    return _report_to_public(project, report)


@router.get("/projects/{project_id}/report/internal", response_model=InternalEvaluationReport)
def get_internal_report(project_id: str, current_user: CurrentFacultyOrHOD, db: DB):
    """Full internal report — faculty/HOD only."""
    project = _get_project_or_404(project_id, db)
    report = _get_or_create_report(project, db)
    return _report_to_internal(project, report)
