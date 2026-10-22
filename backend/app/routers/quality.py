"""HOD-only live quality dashboard API: continuous-evaluation results
(benchmark / graph integrity / faculty agreement, as a time series), recent
live telemetry, and a manual "run the benchmark now" trigger.

Every metric is returned on its own — this module never computes or exposes
a single combined "accuracy %".
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Query

from app.dependencies import DB, CurrentHOD
from app.models.quality import EvalRun, EvalMetric, ScoringTelemetry

router = APIRouter(prefix="/v1/quality", tags=["Quality (HOD)"])


@router.get("/summary")
def summary(current_user: CurrentHOD, db: DB):
    """Latest successful run of each kind, with its metrics — the dashboard's landing view."""
    from app.eval.versioning import compute_fingerprint, component_versions

    out = {"current_method_fingerprint": compute_fingerprint(), "current_versions": component_versions(), "runs": {}}
    for kind in ("benchmark", "graph_integrity", "faculty_agreement", "online_rollup"):
        run = (
            db.query(EvalRun)
            .filter(EvalRun.kind == kind, EvalRun.status == "ok")
            .order_by(EvalRun.started_at.desc())
            .first()
        )
        if not run:
            out["runs"][kind] = None
            continue
        metrics = db.query(EvalMetric).filter(EvalMetric.run_id == run.id).all()
        out["runs"][kind] = {
            "run_id": str(run.id), "started_at": run.started_at.isoformat(),
            "trigger": run.trigger, "label": run.label, "method_fingerprint": run.method_fingerprint,
            "n_cases": run.n_cases, "duration_ms": run.duration_ms,
            "metrics": [
                {
                    "metric": m.metric, "variant": m.variant, "slice": m.slice,
                    "value": m.value, "n": m.n, "ci_low": m.ci_low, "ci_high": m.ci_high,
                    "target": m.target, "target_op": m.target_op, "passed": m.passed, "details": m.details,
                }
                for m in metrics
            ],
        }
    return out


@router.get("/timeseries")
def timeseries(
    current_user: CurrentHOD, db: DB,
    metric: str = Query(...),
    variant: str = Query("graph_only"),
    slice: str = Query("all"),
    days: int = Query(30, ge=1, le=365),
):
    """History of one metric over time, for a trend chart."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (
        db.query(EvalMetric, EvalRun.started_at, EvalRun.label)
        .join(EvalRun, EvalRun.id == EvalMetric.run_id)
        .filter(
            EvalMetric.metric == metric, EvalMetric.variant == variant, EvalMetric.slice == slice,
            EvalRun.started_at >= since, EvalRun.status == "ok",
        )
        .order_by(EvalRun.started_at.asc())
        .all()
    )
    return {
        "metric": metric, "variant": variant, "slice": slice,
        "points": [
            {"started_at": started_at.isoformat(), "label": label, "value": m.value, "n": m.n,
             "ci_low": m.ci_low, "ci_high": m.ci_high, "passed": m.passed}
            for m, started_at, label in rows
        ],
    }


@router.get("/ablation")
def ablation(current_user: CurrentHOD, db: DB):
    """Latest benchmark's metrics grouped by variant (semantic_only / graph_only
    / combined / entity_only / token_only) — whichever variants exist yet.
    Phase 0 only ever has graph_only; later phases add the rest."""
    run = (
        db.query(EvalRun)
        .filter(EvalRun.kind == "benchmark", EvalRun.status == "ok")
        .order_by(EvalRun.started_at.desc())
        .first()
    )
    if not run:
        return {"run_id": None, "variants": {}}
    metrics = db.query(EvalMetric).filter(EvalMetric.run_id == run.id).all()
    by_variant: dict[str, list[dict]] = {}
    for m in metrics:
        by_variant.setdefault(m.variant, []).append({
            "metric": m.metric, "slice": m.slice, "value": m.value, "n": m.n, "passed": m.passed,
        })
    return {"run_id": str(run.id), "started_at": run.started_at.isoformat(), "variants": by_variant}


@router.get("/runs")
def list_runs(current_user: CurrentHOD, db: DB, kind: str | None = None, limit: int = Query(50, le=200)):
    q = db.query(EvalRun)
    if kind:
        q = q.filter(EvalRun.kind == kind)
    rows = q.order_by(EvalRun.started_at.desc()).limit(limit).all()
    return [
        {
            "run_id": str(r.id), "kind": r.kind, "trigger": r.trigger, "status": r.status,
            "label": r.label, "method_fingerprint": r.method_fingerprint,
            "started_at": r.started_at.isoformat(), "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "duration_ms": r.duration_ms, "n_cases": r.n_cases, "error": r.error,
        }
        for r in rows
    ]


@router.get("/telemetry/recent")
def recent_telemetry(current_user: CurrentHOD, db: DB, limit: int = Query(50, le=200)):
    rows = db.query(ScoringTelemetry).order_by(ScoringTelemetry.created_at.desc()).limit(limit).all()
    return [
        {
            "run_id": r.run_id, "project_id": str(r.project_id), "status": r.status,
            "failed_stage": r.failed_stage, "total_ms": r.total_ms,
            "novelty_score": r.novelty_score, "overall_score": r.overall_score,
            "invariants_passed": r.invariants_passed, "evidence_quality": r.evidence_quality,
            "corpus_key_coverage": r.corpus_key_coverage, "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/faculty-agreement")
def faculty_agreement_latest(current_user: CurrentHOD, db: DB):
    run = (
        db.query(EvalRun)
        .filter(EvalRun.kind == "faculty_agreement", EvalRun.status == "ok")
        .order_by(EvalRun.started_at.desc())
        .first()
    )
    if not run:
        return {"run_id": None, "metrics": [], "note": "No faculty-agreement run yet."}
    metrics = db.query(EvalMetric).filter(EvalMetric.run_id == run.id).all()
    return {
        "run_id": str(run.id), "started_at": run.started_at.isoformat(),
        "metrics": [{"metric": m.metric, "value": m.value, "n": m.n, "details": m.details} for m in metrics],
        "note": "Shown for n>=10; treat as unreliable below n=30 — see each metric's n.",
    }


@router.post("/benchmark/run")
def trigger_benchmark(current_user: CurrentHOD, label: str | None = None):
    """Manually queue a benchmark run (on the 'eval' queue, not blocking submissions)."""
    from app.tasks.evaluation import run_benchmark_task

    result = run_benchmark_task.delay(trigger="manual", label=label)
    return {"queued": True, "task_id": result.id}
