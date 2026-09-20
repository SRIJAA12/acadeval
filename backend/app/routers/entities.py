"""
Module 3 \u2014 Entity Knowledge Base & Pending-Review Router
==========================================================
Exposes the AcadEval_FeatureKnowledgeBase and the pending-review workflow
(Section 7, Steps 6-7) so faculty can approve / reject new entity candidates
that the LLM flagged as genuinely novel terms not in the existing KB.

Routes:
  GET  /api/entities/knowledge-base          \u2014 browse KB (all authenticated users)
  GET  /api/entities/project/{project_id}    \u2014 stored extraction result for a project
  GET  /api/entities/pending-review          \u2014 list unapproved candidates (faculty/HOD)
  POST /api/entities/pending-review/{name}/approve \u2014 add to KB (faculty/HOD)
  POST /api/entities/pending-review/{name}/reject  \u2014 remove from queue (faculty/HOD)
"""

import json
import logging
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.dependencies import DB, CurrentUser, CurrentFacultyOrHOD
from app.models.project import Project
from app.services.graph_db import graph_service

log = logging.getLogger(__name__)

router = APIRouter(prefix="/entities", tags=["Module 3 — Entity Knowledge Base"])

# ── FeatureKB file paths (same as extractor.py) ───────────────────────────────
FEATURE_KB_DIR = Path(__file__).resolve().parents[3] / "datasets" / "feature_kb"
PENDING_REVIEW_PATH = FEATURE_KB_DIR / "pending_review.json"
FEATURE_KB_JSON = FEATURE_KB_DIR / "AcadEval_FeatureKnowledgeBase.json"
FEATURE_KB_CSV = FEATURE_KB_DIR / "AcadEval_FeatureKnowledgeBase.csv"

# Load helpers from dataset directory
sys.path.insert(0, str(FEATURE_KB_DIR))
try:
    from feature_kb_loader import load_feature_list
except ImportError:
    load_feature_list = None  # type: ignore


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class KBEntry(BaseModel):
    name: str
    category: str
    aliases: list[str] = []
    first_seen_year: Optional[int] = None
    description: Optional[str] = None


class PendingReviewItem(BaseModel):
    name: str
    category: str
    source_project_id: Optional[str] = None
    queued_at: Optional[str] = None


class ApproveRequest(BaseModel):
    category: str
    aliases: list[str] = []
    first_seen_year: Optional[int] = None
    description: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_pending() -> list[dict]:
    """Read pending_review.json; returns [] if file missing or malformed."""
    try:
        if PENDING_REVIEW_PATH.exists():
            return json.loads(PENDING_REVIEW_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Could not read pending_review.json: %s", e)
    return []


def _write_pending(queue: list[dict]) -> None:
    try:
        PENDING_REVIEW_PATH.write_text(json.dumps(queue, indent=2), encoding="utf-8")
    except Exception as e:
        log.error("Could not write pending_review.json: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update pending review queue.")


def _append_to_kb(entry: dict) -> None:
    """
    Append an approved entry to AcadEval_FeatureKnowledgeBase.json.
    The extractor_service will pick it up on the next extraction call
    because feature_kb_loader.load_feature_list() reads fresh from disk.
    """
    try:
        existing: list[dict] = []
        if FEATURE_KB_JSON.exists():
            existing = json.loads(FEATURE_KB_JSON.read_text(encoding="utf-8"))
        # Avoid duplicates
        names_lower = {e["name"].lower() for e in existing}
        if entry["name"].lower() not in names_lower:
            existing.append(entry)
            FEATURE_KB_JSON.write_text(json.dumps(existing, indent=2), encoding="utf-8")
            log.info("Approved and added to FeatureKB: %r (%s)", entry["name"], entry["category"])
        else:
            log.info("Entry %r already in FeatureKB; skipping duplicate.", entry["name"])
    except Exception as e:
        log.error("Failed to append to FeatureKB JSON: %s", e)
        raise HTTPException(status_code=500, detail="Failed to update FeatureKnowledgeBase.")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/knowledge-base", summary="Browse the AcadEval FeatureKnowledgeBase")
def list_knowledge_base(
    current_user: CurrentUser,
    category: Optional[str] = Query(None, description="Filter by category (algorithm, technology, ...)"),
    search: Optional[str] = Query(None, description="Case-insensitive name search"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Returns a paginated view of AcadEval_FeatureKnowledgeBase.
    Available to all authenticated users (students can see what entities the system knows).
    """
    if not load_feature_list:
        raise HTTPException(status_code=503, detail="FeatureKnowledgeBase loader not available.")

    feats = load_feature_list()

    # Optional filters
    if category:
        feats = [f for f in feats if f.get("category", "").lower() == category.lower()]
    if search:
        q = search.lower()
        feats = [
            f for f in feats
            if q in f.get("name", "").lower()
            or any(q in a.lower() for a in f.get("aliases", []))
        ]

    total = len(feats)
    page = feats[offset: offset + limit]

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "entries": page,
    }


@router.get("/project/{project_id}", summary="Get stored entity extraction for a project")
def get_project_entities(project_id: str, current_user: CurrentUser, db: DB):
    """
    Returns the cached Module 3 extraction result stored on the project row.
    If extracted_entities is missing, dynamically runs FeatureExtractorService.
    """
    try:
        import uuid as _uuid
        pid = _uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project_id format.")

    project = db.query(Project).filter(Project.id == pid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # Role check: students can only see their own projects
    from app.models.user import UserRole
    if current_user.role == UserRole.student and project.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    extracted = project.extracted_entities
    # Trigger re-extraction if: never run (None) OR all lists are empty (prior extraction bug)
    entity_lists_empty = extracted is not None and all(
        len(v) == 0 for v in extracted.values() if isinstance(v, list)
    )
    if extracted is None or entity_lists_empty:
        from app.services.extractor import extractor_service
        from app.services.document_parser import document_parser_service
        from pathlib import Path as _Path
        try:
            # Build the richest possible text for extraction
            file_texts = []
            for pf in (project.files or []):
                if pf.storage_path and _Path(pf.storage_path).exists():
                    try:
                        parsed = document_parser_service.parse_uploaded_file(
                            file_path=pf.storage_path, filename=pf.original_filename
                        )
                        file_texts.append(parsed.get("raw_text", ""))
                    except Exception:
                        pass

            full_text = "\n".join(filter(None, [
                project.title,
                project.domain or "",
            ] + file_texts)) or project.title

            extracted = extractor_service.extract_entities(full_text)
            project.extracted_entities = extracted
            db.commit()
            log.info("Dynamic extraction saved %d entity types for project %s", len(extracted), project_id)
        except Exception as ee:
            log.warning("Dynamic entity extraction failed for project %s: %s", project_id, ee)
            extracted = {}

    return {
        "project_id": project_id,
        "title": project.title,
        "extracted_entities": extracted,
        "has_been_extracted": True,
    }


@router.get("/pending-review", summary="List new entity candidates awaiting faculty approval")
def list_pending_review(current_user: CurrentFacultyOrHOD):
    """
    Returns all terms the LLM flagged as genuinely new (not in FeatureKB)
    waiting for a faculty member to approve or reject them.
    """
    queue = _read_pending()
    return {
        "total": len(queue),
        "items": queue,
    }


@router.post("/pending-review/{name}/approve", summary="Approve a pending entity into the FeatureKnowledgeBase")
def approve_pending(
    name: str,
    body: ApproveRequest,
    current_user: CurrentFacultyOrHOD,
):
    """
    Moves the named candidate out of pending_review.json and appends it to
    AcadEval_FeatureKnowledgeBase.json with the supplied metadata.
    The extractor service will use it on the next extraction call.
    """
    queue = _read_pending()
    original = next((item for item in queue if item["name"].lower() == name.lower()), None)
    if not original:
        raise HTTPException(status_code=404, detail=f"No pending entry named {name!r}.")

    new_entry = {
        "name": original["name"],
        "category": body.category or original.get("category", "technology"),
        "aliases": body.aliases,
        "first_seen_year": body.first_seen_year,
        "description": body.description,
    }
    _append_to_kb(new_entry)

    # Remove from pending queue
    queue = [item for item in queue if item["name"].lower() != name.lower()]
    _write_pending(queue)

    return {
        "status": "approved",
        "entry": new_entry,
        "pending_remaining": len(queue),
    }


@router.post("/pending-review/{name}/reject", summary="Reject and remove a pending entity candidate")
def reject_pending(name: str, current_user: CurrentFacultyOrHOD):
    """
    Permanently removes the named candidate from pending_review.json without
    adding it to the FeatureKnowledgeBase.
    """
    queue = _read_pending()
    original = next((item for item in queue if item["name"].lower() == name.lower()), None)
    if not original:
        raise HTTPException(status_code=404, detail=f"No pending entry named {name!r}.")

    queue = [item for item in queue if item["name"].lower() != name.lower()]
    _write_pending(queue)

    return {
        "status": "rejected",
        "removed": original["name"],
        "pending_remaining": len(queue),
    }


# ── Neo4j Graph Health & Stats (Module 3 ↔ Module 4 bridge) ──────────────────

@router.get("/graph/health", summary="Check Neo4j Aura connectivity")
def graph_health(current_user: CurrentUser):
    """
    Pings the Neo4j Aura instance and returns connection status.
    Use this to verify your .env NEO4J_* credentials are working.
    """
    return graph_service.ping()


@router.get("/graph/stats", summary="Live node and edge counts from Neo4j")
def graph_stats(current_user: CurrentFacultyOrHOD):
    """
    Returns the count of each node label (Project, Algorithm, Technology, etc.)
    and total relationships in the AcadEval graph.
    Requires faculty/HOD role.
    """
    return graph_service.get_graph_stats()


@router.post("/graph/ingest/{project_id}", summary="Manually trigger Neo4j ingestion for a project")
def ingest_project_graph(project_id: str, current_user: CurrentFacultyOrHOD, db: DB):
    """
    Re-runs (or first-time runs) the Neo4j graph write for a project
    that already has extracted_entities stored in PostgreSQL.
    Useful if Neo4j was down during submission.
    """
    import uuid as _uuid
    try:
        pid = _uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid project_id format.")

    project = db.query(Project).filter(Project.id == pid).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    if not project.extracted_entities:
        raise HTTPException(
            status_code=400,
            detail="This project has no extracted_entities yet. Submit it through the AcadEval+ pipeline first.",
        )

    if not project.evaluation or not project.evaluation.novelty_report:
        raise HTTPException(
            status_code=409,
            detail="Novelty evidence must be persisted before graph ingestion.",
        )

    from app.services.graph_db import GraphUnavailableError
    try:
        from datetime import datetime, timezone
        from app.services.graph_builder import ingest_project_to_relational_graph
        from app.services.graph_db import GRAPH_INGESTION_VERSION

        result = ingest_project_to_relational_graph(
            db=db,
            project_id=str(project.id),
            title=project.title or "",
            domain=project.domain or "Unknown",
            sub_domain=project.extracted_entities.get("sub_domain", "Unknown"),
            extracted_entities=project.extracted_entities,
        )
        project.graph_ingested_at = datetime.now(timezone.utc)
        project.graph_ingestion_version = GRAPH_INGESTION_VERSION
        db.commit()
        return {"status": "ingested", **result}
    except GraphUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
