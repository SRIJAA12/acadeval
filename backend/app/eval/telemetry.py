"""Live telemetry for the scoring pipeline: one ScoringTelemetry row per
Celery chain run, with per-stage timing and a set of invariant checks run on
every submission (not just in the offline benchmark). See app/tasks/pipeline.py
for how `stage()` wraps each task, and `finalize_run()` for the closing checks.

Telemetry writes use their own short-lived DB session and are always
best-effort: a telemetry failure must never fail or roll back a real
submission's scoring.
"""
from __future__ import annotations

import logging
import math
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

log = logging.getLogger(__name__)

# Known-false explanation claims found in the current codebase (acadeval_plus.py,
# explainability.py) — methods that are described but never actually run.
# Phase 4 rewrites explanations to be structured and evidence-backed; until
# then this just measures how often the false claims appear.
FORBIDDEN_EXPLANATION_PHRASES = [
    "adamic-adar", "simbench calibration", "calibrated against simbench",
    "all-mpnet-base-v2", "sbert+tf-idf", "sbert + tf-idf", "sbert + bm25",
]

REPEATABILITY_SAMPLE_EVERY = 20  # re-check 1 in N runs — the recheck re-reads the full Neo4j snapshot


def _session():
    from app.database import SessionLocal
    return SessionLocal()


def ensure_run(project_id: str, run_id: str) -> None:
    """Idempotent: creates the telemetry row for this run if it doesn't exist yet."""
    from app.models.quality import ScoringTelemetry

    db = _session()
    try:
        exists = db.query(ScoringTelemetry.id).filter_by(run_id=run_id).first()
        if exists:
            return
        db.add(ScoringTelemetry(
            id=uuid.uuid4(),
            project_id=uuid.UUID(str(project_id)),
            run_id=run_id,
            status="running",
            started_at=datetime.now(timezone.utc),
            stage_ms={},
            versions={},
            invariants={},
        ))
        db.commit()
    except Exception:
        db.rollback()
        log.exception("telemetry.ensure_run failed for run_id=%s (non-fatal)", run_id)
    finally:
        db.close()


def _record_stage_ms(run_id: str, stage_name: str, ms: float) -> None:
    from app.models.quality import ScoringTelemetry

    db = _session()
    try:
        row = db.query(ScoringTelemetry).filter_by(run_id=run_id).first()
        if row:
            stage_ms = dict(row.stage_ms or {})
            stage_ms[stage_name] = round(ms, 1)
            row.stage_ms = stage_ms
            db.commit()
    except Exception:
        db.rollback()
        log.exception("telemetry._record_stage_ms failed for run_id=%s (non-fatal)", run_id)
    finally:
        db.close()


def mark_failed(run_id: str, stage_name: str, exc: BaseException) -> None:
    from app.models.quality import ScoringTelemetry

    db = _session()
    try:
        row = db.query(ScoringTelemetry).filter_by(run_id=run_id).first()
        if row:
            row.status = "failed"
            row.failed_stage = stage_name
            row.error_class = type(exc).__name__
            row.finished_at = datetime.now(timezone.utc)
            db.commit()
    except Exception:
        db.rollback()
        log.exception("telemetry.mark_failed failed for run_id=%s (non-fatal)", run_id)
    finally:
        db.close()


def stage_start(project_id: str, run_id: str | None, stage_name: str) -> float | None:
    """Call at the top of a pipeline task. Returns a timer token (or None if
    run_id is None, e.g. a task invoked outside a Celery chain) to pass to
    stage_end(). Explicit start/end rather than a context manager so existing
    task bodies don't need re-indenting to adopt this."""
    if not run_id:
        return None
    ensure_run(project_id, run_id)
    return time.monotonic()


def stage_end(run_id: str | None, stage_name: str, t0: float | None) -> None:
    """Call on every exit path of a pipeline task (success, early return, or
    in the except block) — safe to call more than once; the last call wins.
    Does NOT mark the run failed — a task may retry and later succeed, so
    only the caller (which knows whether this was the final retry) should do
    that, via mark_failed()."""
    if t0 is None or not run_id:
        return
    _record_stage_ms(run_id, stage_name, (time.monotonic() - t0) * 1000)


@contextmanager
def stage(project_id: str, run_id: str | None, stage_name: str):
    """Context-manager form of stage_start/stage_end, for call sites that
    control their whole block (e.g. the eval tasks themselves)."""
    t0 = stage_start(project_id, run_id, stage_name)
    try:
        yield
    finally:
        stage_end(run_id, stage_name, t0)


def _check_invariants(eval_report, assessment_evidence: dict) -> dict:
    """Score-bound / NaN / grade-consistency checks run on every submission."""
    from app.services.assessment_engine import grade_for

    checks: dict[str, bool] = {}

    def in_range(value, lo, hi) -> bool:
        if value is None:
            return True
        try:
            return lo <= float(value) <= hi and not math.isnan(float(value))
        except (TypeError, ValueError):
            return False

    checks["overall_score_in_range"] = in_range(eval_report.overall_score, 0, 100)
    checks["novelty_score_in_range"] = in_range(eval_report.novelty_score, 0, 100)
    for dim in ("feasibility_score", "completeness_score", "technical_depth_score",
                "clarity_score", "similarity_risk_score", "publication_potential_score"):
        checks[f"{dim}_in_range"] = in_range(getattr(eval_report, dim, None), 0, 100)

    signals = (eval_report.novelty_report or {}).get("signals_breakdown", {})
    checks["signals_in_range"] = all(in_range(v, 0, 1) for v in signals.values()) if signals else True

    if eval_report.overall_score is not None:
        expected_grade = grade_for(eval_report.overall_score)
        checks["grade_matches_score"] = (eval_report.grade == expected_grade)
    else:
        checks["grade_matches_score"] = True

    checks["duplicate_flag_consistent"] = not (
        eval_report.is_duplicate and (eval_report.similarity_risk_score or 0) < 50
    )
    return checks


def _explanation_coverage(novelty_report: dict) -> tuple[int, int, int]:
    """(claims, backed, forbidden). "backed" is a Phase-0 approximation — a
    claim counts as backed unless it contains a known-false method reference.
    Phase 4 replaces this with real evidence-reference checking."""
    lines = (novelty_report or {}).get("explanation_lines", []) or []
    claims = len(lines)
    forbidden = 0
    for line in lines:
        low = str(line).lower()
        if any(phrase in low for phrase in FORBIDDEN_EXPLANATION_PHRASES):
            forbidden += 1
    backed = claims - forbidden
    return claims, backed, forbidden


def _corpus_key_coverage(extracted_entities: dict) -> tuple[int, float | None]:
    try:
        from app.services.corpus_matcher import get_corpus_vocabulary
        vocab = get_corpus_vocabulary()
    except Exception:
        return 0, None

    keys = set()
    for key, items in (extracted_entities or {}).items():
        if key.startswith("_") or key in ("sub_domain", "domain"):
            continue
        if isinstance(items, list):
            keys.update(str(i).strip().lower() for i in items if i)
    if not keys:
        return 0, None
    coverage = len(keys & vocab) / len(keys)
    return len(keys), round(coverage, 4)


def _repeatability_check(project, entities: dict, domain: str, sub_domain: str, stored_score: float | None) -> tuple[bool, float | None]:
    """Re-invokes the (read-only) novelty computation and compares the
    composite score to what was just stored. Sampled, not run every time —
    see REPEATABILITY_SAMPLE_EVERY."""
    if stored_score is None:
        return False, None
    try:
        import hashlib
        sample_key = int(hashlib.sha256(str(project.id).encode()).hexdigest(), 16)
        if sample_key % REPEATABILITY_SAMPLE_EVERY != 0:
            return False, None

        from app.services.novelty_engine import novelty_engine_service
        repeat = novelty_engine_service.compute_novelty_signals(
            project_id=str(project.id), extracted_entities=entities, domain=domain, sub_domain=sub_domain,
        )
        delta = abs(float(repeat["composite_novelty_score"]) - float(stored_score))
        return True, round(delta, 4)
    except Exception:
        log.exception("telemetry repeatability check failed for %s (non-fatal)", project.id)
        return False, None


def finalize_run(project, run_id: str | None, eval_report, entities: dict, domain: str, sub_domain: str) -> None:
    """Called once, at the end of task_score_and_report, after eval_report is
    committed. Writes the closing fields onto the run's telemetry row."""
    if not run_id:
        return
    from app.models.quality import ScoringTelemetry
    from app.eval.versioning import compute_fingerprint, component_versions

    db = _session()
    try:
        row = db.query(ScoringTelemetry).filter_by(run_id=run_id).first()
        if not row:
            return
        if row.status == "failed":
            db.commit()
            return

        band = (eval_report.novelty_report or {}).get("overall_novelty_band", "") or ""
        row.status = "insufficient" if "Insufficient" in band else "ok"
        row.finished_at = datetime.now(timezone.utc)
        row.total_ms = round(sum((row.stage_ms or {}).values()), 1)

        row.method_fingerprint = compute_fingerprint()
        row.versions = component_versions()

        row.novelty_score = eval_report.novelty_score
        row.overall_score = eval_report.overall_score
        similar = (eval_report.novelty_report or {}).get("most_similar_projects", []) or []
        row.top1_similarity = similar[0]["similarity_score"] if similar else None
        row.is_duplicate = eval_report.is_duplicate

        invariants = _check_invariants(eval_report, eval_report.assessment_evidence or {})
        row.invariants = invariants
        row.invariants_passed = all(invariants.values())

        claims, backed, forbidden = _explanation_coverage(eval_report.novelty_report or {})
        row.explanation_claims, row.explanation_backed, row.forbidden_claims = claims, backed, forbidden

        metadata = (eval_report.novelty_report or {}).get("scoring_metadata", {})
        row.evidence_quality = metadata.get("evidence_quality")

        entity_count, coverage = _corpus_key_coverage(entities)
        row.entity_count, row.corpus_key_coverage = entity_count, coverage

        checked, max_delta = _repeatability_check(project, entities, domain, sub_domain, eval_report.novelty_score)
        row.repeat_checked, row.repeat_max_abs_delta = checked, max_delta

        db.commit()
    except Exception:
        db.rollback()
        log.exception("telemetry.finalize_run failed for run_id=%s (non-fatal)", run_id)
    finally:
        db.close()
