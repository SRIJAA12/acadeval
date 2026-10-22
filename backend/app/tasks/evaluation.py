"""Continuous-evaluation Celery tasks: the benchmark, graph-integrity checks,
and faculty-agreement correlation, run on a schedule AND automatically
whenever the scoring method's fingerprint changes (see app/eval/versioning.py).
Routed to the "eval" queue (app/worker.py) so a long benchmark run never
blocks real submissions on the "pipeline" queue.
"""
from __future__ import annotations

import logging

from celery.utils.log import get_task_logger

from app.worker import celery_app

log = get_task_logger(__name__)


def _get_db():
    from app.database import SessionLocal
    return SessionLocal()


@celery_app.task(name="eval.run_benchmark", bind=True, max_retries=0, time_limit=1800, soft_time_limit=1700)
def run_benchmark_task(self, trigger: str = "manual", label: str | None = None):
    from app.eval.benchmark_runner import run_benchmark

    db = _get_db()
    try:
        run = run_benchmark(db, trigger=trigger, label=label)
        log.info("eval.run_benchmark (%s) finished: status=%s n_cases=%s duration_ms=%s",
                  trigger, run.status, run.n_cases, run.duration_ms)
        return {"run_id": str(run.id), "status": run.status}
    finally:
        db.close()


@celery_app.task(name="eval.run_graph_integrity", bind=True, max_retries=0)
def run_graph_integrity_task(self, trigger: str = "manual"):
    import uuid
    from datetime import datetime, timezone
    from app.eval.graph_integrity import run_graph_integrity_checks
    from app.eval.versioning import compute_fingerprint, component_versions
    from app.models.quality import EvalRun, EvalMetric
    from app.services.graph_db import GraphUnavailableError

    db = _get_db()
    run = EvalRun(
        id=uuid.uuid4(), kind="graph_integrity", trigger=trigger, status="running",
        method_fingerprint=compute_fingerprint(), versions=component_versions(),
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    import time
    t0 = time.monotonic()
    try:
        results = run_graph_integrity_checks()
        rows = [
            EvalMetric(run_id=run.id, metric=name, variant="-", slice="all",
                       value=info["value"], n=info["n"], details=info["details"])
            for name, info in results.items()
        ]
        db.add_all(rows)
        run.status = "ok"
    except GraphUnavailableError as exc:
        run.status = "failed"
        run.error = f"Neo4j unavailable: {exc}"
        log.warning("eval.run_graph_integrity: Neo4j unavailable (%s)", exc)
    except Exception as exc:
        log.exception("eval.run_graph_integrity failed")
        run.status = "failed"
        run.error = str(exc)[:2000]
    finally:
        run.finished_at = datetime.now(timezone.utc)
        run.duration_ms = round((time.monotonic() - t0) * 1000, 1)
        db.commit()
        result = {"run_id": str(run.id), "status": run.status}
        db.close()
    return result


@celery_app.task(name="eval.run_faculty_agreement", bind=True, max_retries=0)
def run_faculty_agreement_task(self, trigger: str = "manual"):
    import uuid
    import time
    from datetime import datetime, timezone
    from app.eval.faculty_agreement import compute_faculty_agreement
    from app.eval.versioning import compute_fingerprint, component_versions
    from app.models.quality import EvalRun, EvalMetric

    db = _get_db()
    run = EvalRun(
        id=uuid.uuid4(), kind="faculty_agreement", trigger=trigger, status="running",
        method_fingerprint=compute_fingerprint(), versions=component_versions(),
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    t0 = time.monotonic()
    try:
        results = compute_faculty_agreement(db)
        rows = [
            EvalMetric(run_id=run.id, metric=name, variant="-", slice="all",
                       value=info["value"], n=info["n"], details=info["details"])
            for name, info in results.items()
        ]
        db.add_all(rows)
        run.status = "ok"
    except Exception as exc:
        log.exception("eval.run_faculty_agreement failed")
        run.status = "failed"
        run.error = str(exc)[:2000]
    finally:
        run.finished_at = datetime.now(timezone.utc)
        run.duration_ms = round((time.monotonic() - t0) * 1000, 1)
        db.commit()
        result = {"run_id": str(run.id), "status": run.status}
        db.close()
    return result


@celery_app.task(name="eval.rollup_online", bind=True, max_retries=0)
def rollup_online_task(self, window_hours: int = 1):
    """Aggregates the last `window_hours` of scoring_telemetry rows into
    EvalMetric rows (latency, failure rate, invariant pass rate, ...) — this
    is how "online" telemetry becomes a dashboard time series without
    querying raw telemetry rows from the frontend."""
    import uuid
    import time
    from datetime import datetime, timezone, timedelta
    from app.eval.versioning import compute_fingerprint, component_versions
    from app.models.quality import EvalRun, EvalMetric, ScoringTelemetry

    db = _get_db()
    run = EvalRun(
        id=uuid.uuid4(), kind="online_rollup", trigger="schedule", status="running",
        method_fingerprint=compute_fingerprint(), versions=component_versions(),
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    t0 = time.monotonic()
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        rows = db.query(ScoringTelemetry).filter(ScoringTelemetry.created_at >= since).all()
        run.n_cases = len(rows)

        metric_rows = []
        if rows:
            import numpy as np
            total = len(rows)
            failed = sum(1 for r in rows if r.status == "failed")
            stuck = sum(1 for r in rows if r.status == "running" and
                        (datetime.now(timezone.utc) - r.started_at.replace(tzinfo=timezone.utc)).total_seconds() > 1800)
            metric_rows.append(EvalMetric(run_id=run.id, metric="failure_rate", variant="-", slice="all",
                                           value=round((failed + stuck) / total, 4), n=total,
                                           details={"failed": failed, "stuck": stuck}))

            invariant_checked = [r for r in rows if r.invariants_passed is not None]
            if invariant_checked:
                rate = sum(1 for r in invariant_checked if r.invariants_passed) / len(invariant_checked)
                metric_rows.append(EvalMetric(run_id=run.id, metric="invalid_score_rate", variant="-", slice="all",
                                               value=round(1 - rate, 4), n=len(invariant_checked)))

            repeat_checked = [r for r in rows if r.repeat_checked and r.repeat_max_abs_delta is not None]
            if repeat_checked:
                rate = sum(1 for r in repeat_checked if r.repeat_max_abs_delta <= 1e-6) / len(repeat_checked)
                metric_rows.append(EvalMetric(run_id=run.id, metric="repeatability", variant="-", slice="all",
                                               value=round(rate, 4), n=len(repeat_checked)))

            explained = [r for r in rows if r.explanation_claims]
            if explained:
                claims = sum(r.explanation_claims for r in explained)
                backed = sum(r.explanation_backed or 0 for r in explained)
                forbidden = sum(r.forbidden_claims or 0 for r in explained)
                metric_rows.append(EvalMetric(run_id=run.id, metric="explanation_coverage", variant="-", slice="all",
                                               value=round(backed / claims, 4) if claims else None, n=claims))
                metric_rows.append(EvalMetric(run_id=run.id, metric="forbidden_explanation_claims", variant="-", slice="all",
                                               value=float(forbidden), n=claims))

            coverage_vals = [r.corpus_key_coverage for r in rows if r.corpus_key_coverage is not None]
            if coverage_vals:
                metric_rows.append(EvalMetric(run_id=run.id, metric="corpus_key_coverage", variant="-", slice="all",
                                               value=round(float(np.mean(coverage_vals)), 4), n=len(coverage_vals)))

            # Latency per stage, from the stage_ms JSON on each row.
            stage_names = set()
            for r in rows:
                stage_names.update((r.stage_ms or {}).keys())
            for stage_name in stage_names:
                vals = [r.stage_ms[stage_name] for r in rows if r.stage_ms and stage_name in r.stage_ms]
                if vals:
                    arr = np.array(vals)
                    metric_rows.append(EvalMetric(
                        run_id=run.id, metric=f"latency_ms:{stage_name}", variant="-", slice="all",
                        value=round(float(np.mean(arr)), 1), n=len(vals),
                        details={"p95": round(float(np.percentile(arr, 95)), 1), "max": round(float(arr.max()), 1)},
                    ))

        db.add_all(metric_rows)
        run.status = "ok"
    except Exception as exc:
        log.exception("eval.rollup_online failed")
        run.status = "failed"
        run.error = str(exc)[:2000]
    finally:
        run.finished_at = datetime.now(timezone.utc)
        run.duration_ms = round((time.monotonic() - t0) * 1000, 1)
        db.commit()
        result = {"run_id": str(run.id), "status": run.status}
        db.close()
    return result


@celery_app.task(name="eval.check_versions", bind=True, max_retries=0)
def check_versions_task(self):
    """Runs every 10 min (and once at worker startup — see worker.py's
    worker_ready hook, covering the "machine was off overnight" case).
    Compares the live method fingerprint to the most recent successful
    benchmark's fingerprint; if different, triggers a fresh benchmark run."""
    from app.eval.versioning import compute_fingerprint
    from app.models.quality import EvalRun

    db = _get_db()
    try:
        current = compute_fingerprint()
        last = (
            db.query(EvalRun)
            .filter(EvalRun.kind == "benchmark", EvalRun.status == "ok")
            .order_by(EvalRun.started_at.desc())
            .first()
        )
        if last is None:
            log.info("eval.check_versions: no prior benchmark run — triggering baseline run")
            run_benchmark_task.delay(trigger="version_change", label="baseline-v2.0")
            return {"triggered": True, "reason": "no_prior_run"}
        if last.method_fingerprint != current:
            log.info("eval.check_versions: fingerprint changed (%s -> %s) — triggering benchmark",
                      last.method_fingerprint, current)
            run_benchmark_task.delay(trigger="version_change")
            return {"triggered": True, "reason": "fingerprint_changed", "old": last.method_fingerprint, "new": current}
        return {"triggered": False}
    finally:
        db.close()
