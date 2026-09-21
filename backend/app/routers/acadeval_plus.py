"""
AcadEval+ API Router
======================
Exposes the graph-based novelty assessment pipeline (Modules 1-7): domain
classification, entity extraction, Neo4j graph building, novelty scoring,
trend scoring, explainable report assembly, and faculty ground-truth feedback.

Every endpoint operates on a real `Project` row (not an ad-hoc string id), is
authenticated via the same `dependencies.py` pattern as the rest of the app,
and — where the pipeline produces a novelty score — syncs it back onto the
project's `EvaluationReport` so it isn't a second, disconnected system.
"""

import math
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.dependencies import DB, CurrentUser, CurrentFacultyOrHOD
from app.models.project import Project, PipelineStatus
from app.models.evaluation import FacultyEvaluation
from app.models.user import UserRole
from app.services.classifier import classifier_service
from app.services.extractor import extractor_service
from app.services.graph_db import GRAPH_INGESTION_VERSION, GraphUnavailableError
from app.services.trend_scorer import trend_scorer_service

router = APIRouter(prefix="/v1/acadeval", tags=["AcadEval+ Novelty Engine"])

# ── Schemas ───────────────────────────────────────────────────────────────────

class ClassifyRequest(BaseModel):
    title: str
    abstract: str


class EntityExtractRequest(BaseModel):
    text: str


class BuildGraphRequest(BaseModel):
    domain: str
    sub_domain: str
    extracted_entities: dict


class SubmitProposalRequest(BaseModel):
    project_id: uuid.UUID
    abstract: str = Field(..., example="This capstone project proposes a 3D U-Net model with attention for segmenting brain tumors in MRI scans.")
    tech_stack: list[str] = Field(default_factory=list)


class FacultyReviewInput(BaseModel):
    project_id: uuid.UUID
    faculty_score: float = Field(..., ge=1.0, le=10.0, description="Faculty score 1 to 10")
    system_score: float = Field(..., ge=0.0, le=100.0, description="System novelty score 0 to 100")
    override_reason: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_project_or_404(project_id: uuid.UUID, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _require_project_access(project: Project, current_user):
    if current_user.role == UserRole.student and project.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / math.sqrt(var_x * var_y)


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    for rank, idx in enumerate(order, start=1):
        ranks[idx] = float(rank)
    return ranks


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/submit", summary="Submit a project for graph-based novelty assessment")
def submit_proposal(payload: SubmitProposalRequest, current_user: CurrentUser, db: DB):
    """
    Queue the same frozen-snapshot pipeline used by the normal upload route.
    This endpoint never performs an inline ingest-before-score shortcut.
    """
    project = _get_project_or_404(payload.project_id, db)
    _require_project_access(project, current_user)

    from app.tasks.pipeline import enqueue_pipeline

    project.abstract = payload.abstract.strip()
    project.pipeline_status = PipelineStatus.ai_processing
    db.commit()

    result = enqueue_pipeline(str(project.id))
    project.celery_task_id = result.id
    db.commit()
    return {
        "status": "queued",
        "project_id": str(project.id),
        "task_id": result.id,
    }


@router.post("/classify", summary="Module 1: Domain & Sub-domain Classification")
def classify_domain_endpoint(payload: ClassifyRequest, current_user: CurrentFacultyOrHOD):
    """Module 1: Domain & Sub-domain Classification using taxonomy embeddings."""
    return classifier_service.classify_project(payload.title, payload.abstract)


@router.post("/extract-entities", summary="Module 2: Structured Entity Extraction")
def extract_entities_endpoint(payload: EntityExtractRequest, current_user: CurrentFacultyOrHOD):
    """Module 2: Extracts algorithms, technologies, frameworks, datasets from text."""
    return extractor_service.extract_entities(payload.text)


@router.post("/build-graph/{project_id}", summary="Module 3: Project Knowledge Graph Construction")
def build_graph_endpoint(project_id: uuid.UUID, payload: BuildGraphRequest, current_user: CurrentFacultyOrHOD, db: DB):
    """Module 3: Re-ingest the project's persisted, already-scored evidence."""
    project = _get_project_or_404(project_id, db)
    if not project.evaluation or not project.evaluation.novelty_report:
        raise HTTPException(
            status_code=409,
            detail="Score the project before inserting it into the historical graph.",
        )
    try:
        from datetime import datetime, timezone
        from app.services.graph_builder import ingest_project_to_relational_graph

        entities = project.extracted_entities or {}
        result = ingest_project_to_relational_graph(
            db=db,
            project_id=str(project.id),
            title=project.title,
            domain=project.domain or payload.domain,
            sub_domain=entities.get("sub_domain") or payload.sub_domain,
            extracted_entities=entities,
        )
        project.graph_ingested_at = datetime.now(timezone.utc)
        project.graph_ingestion_version = GRAPH_INGESTION_VERSION
        db.commit()
        return result
    except GraphUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/novelty-score/{project_id}", summary="Module 4: Graph Novelty Score")
def get_novelty_score(
    project_id: uuid.UUID, current_user: CurrentUser, db: DB,
):
    """
    Return the persisted, versioned score. Read endpoints never recompute a
    project against a different corpus snapshot.
    """
    project = _get_project_or_404(project_id, db)
    _require_project_access(project, current_user)

    if not project.evaluation or not project.evaluation.novelty_report:
        raise HTTPException(status_code=409, detail="Novelty evidence is not ready.")
    return project.evaluation.novelty_report


@router.get("/trend-score", summary="Module 5: Literature Trend Score")
def get_trend_score(current_user: CurrentUser, topic: str = Query(...)):
    """Module 5: Literature trend score from Semantic Scholar API."""
    return trend_scorer_service.get_topic_trend(topic)


@router.get("/report/{project_id}", summary="Module 6: Explainable Novelty Report")
def get_novelty_report(
    project_id: uuid.UUID,
    current_user: CurrentUser,
    db: DB,
):
    """Return the persisted report produced by the async pipeline (read-only)."""
    project = _get_project_or_404(project_id, db)
    _require_project_access(project, current_user)

    if not project.evaluation or not project.evaluation.novelty_report:
        raise HTTPException(
            status_code=409,
            detail="Novelty report is not ready. Poll the project pipeline status and retry when ready=true.",
        )
    return project.evaluation.novelty_report


@router.post("/faculty-review", summary="Module 7: Faculty Review Ground Truth Submission")
def submit_faculty_review(payload: FacultyReviewInput, current_user: CurrentFacultyOrHOD, db: DB):
    """
    Module 7: Persists a faculty rating (1..10) against the system's novelty
    score (0..100) into `faculty_evaluations`, the ground truth used to
    validate the Graph-Based Novelty Engine.
    """
    project = _get_project_or_404(payload.project_id, db)

    if not project.evaluation or project.evaluation.novelty_score is None:
        raise HTTPException(status_code=409, detail="Persisted system novelty evidence is not ready.")
    persisted_system_score = float(project.evaluation.novelty_score)
    if abs(payload.system_score - persisted_system_score) > 0.01:
        raise HTTPException(
            status_code=409,
            detail="The submitted system score does not match the persisted versioned report.",
        )

    system_scaled = persisted_system_score / 10.0
    delta = abs(payload.faculty_score - system_scaled)

    evaluation = FacultyEvaluation(
        project_id=project.id,
        evaluator_id=current_user.id,
        faculty_score=payload.faculty_score,
        system_score=persisted_system_score,
        score_delta=round(delta, 2),
        override_reason=payload.override_reason,
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    return {
        "status": "recorded",
        "id": str(evaluation.id),
        "project_id": str(project.id),
        "faculty_score": payload.faculty_score,
        "system_score": persisted_system_score,
        "score_delta": evaluation.score_delta,
    }


@router.get("/correlation", summary="Module 7: Faculty-vs-System Score Correlation")
def get_correlation(current_user: CurrentFacultyOrHOD, db: DB):
    """
    Recomputes Pearson/Spearman correlation between faculty_score and
    system_score across every recorded FacultyEvaluation — the core
    evaluation result validating (or disproving) the novelty engine.
    """
    rows = db.query(FacultyEvaluation).all()
    if len(rows) < 3:
        return {
            "status": "insufficient_data",
            "sample_size": len(rows),
            "message": "Need at least 3 faculty evaluations to compute a meaningful correlation.",
        }

    faculty_scores = [r.faculty_score for r in rows]
    system_scores = [r.system_score / 10.0 for r in rows]

    pearson_r = _pearson(faculty_scores, system_scores)
    spearman_r = _pearson(_rank(faculty_scores), _rank(system_scores))

    return {
        "status": "ok",
        "sample_size": len(rows),
        "pearson_r": round(pearson_r, 4),
        "spearman_r": round(spearman_r, 4),
    }
