"""
Module 11 — Celery Beat Scheduled Tasks
=========================================
Periodic background jobs that run on a fixed schedule without any human trigger.

Schedule (configured in worker.py celery_app.conf.beat_schedule):
  - refresh_trend_base       : every Sunday 00:00 UTC — re-crawls Semantic Scholar
  - nightly_correlation      : every night   02:00 UTC — Pearson correlation between
                               faculty manual scores and system novelty scores
  - retry_pending_neo4j_sync : every 15 min           — re-attempts Neo4j sync for
                               projects whose graph write succeeded in Postgres
                               but failed against Neo4j (see graph_builder.py)
"""

from __future__ import annotations

import logging

from celery.utils.log import get_task_logger

from app.worker import celery_app

log = get_task_logger(__name__)


@celery_app.task(name="scheduled.refresh_trend_base", bind=True, max_retries=1)
def refresh_trend_base(self):
    """
    Weekly — refresh AcadEval_TrendBase from Semantic Scholar.
    Pulls recent publication counts for every topic in the trend scorer's
    topic list and writes the results back to the dataset CSV / DB table.
    """
    try:
        from app.services.trend_scorer import trend_scorer_service
        log.info("scheduled.refresh_trend_base — starting")

        # trend_scorer_service exposes a refresh hook; call it if available
        if hasattr(trend_scorer_service, "refresh_trend_data"):
            trend_scorer_service.refresh_trend_data()
            log.info("scheduled.refresh_trend_base — trend data refreshed")
        else:
            log.info("scheduled.refresh_trend_base — no refresh hook found, skipping")

        return {"status": "ok"}
    except Exception as exc:
        log.exception("refresh_trend_base failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(name="scheduled.nightly_correlation", bind=True, max_retries=1)
def nightly_correlation(self):
    """
    Nightly — recompute Pearson / Spearman correlation between faculty manual
    scores and AcadEval+ system novelty scores across all reviewed projects.
    Result is written to a correlation_log table or logged for monitoring.
    """
    try:
        import math
        from app.database import SessionLocal
        from app.models.project import Project
        from app.models.evaluation import EvaluationReport, FacultyEvaluation

        db = SessionLocal()
        log.info("scheduled.nightly_correlation — starting")

        try:
            # Load all projects that have both a faculty score and a system score
            rows = (
                db.query(
                    EvaluationReport.novelty_score,
                    FacultyEvaluation.faculty_score,
                )
                .join(Project, Project.id == EvaluationReport.project_id)
                .join(FacultyEvaluation, FacultyEvaluation.project_id == Project.id)
                .filter(
                    EvaluationReport.novelty_score.isnot(None),
                    FacultyEvaluation.faculty_score.isnot(None),
                )
                .all()
            )

            if len(rows) < 3:
                log.info("nightly_correlation — not enough data (%d rows), skipping", len(rows))
                return {"status": "skipped", "reason": "insufficient_data", "n": len(rows)}

            system_scores = [float(r[0]) for r in rows]
            faculty_scores = [float(r[1]) for r in rows]
            n = len(system_scores)

            mean_s = sum(system_scores) / n
            mean_f = sum(faculty_scores) / n
            cov = sum((s - mean_s) * (f - mean_f) for s, f in zip(system_scores, faculty_scores))
            var_s = sum((s - mean_s) ** 2 for s in system_scores)
            var_f = sum((f - mean_f) ** 2 for f in faculty_scores)
            pearson = (cov / math.sqrt(var_s * var_f)) if var_s > 0 and var_f > 0 else 0.0

            log.info(
                "nightly_correlation — n=%d  Pearson r=%.4f  system_mean=%.2f  faculty_mean=%.2f",
                n, pearson, mean_s, mean_f,
            )
            return {
                "status": "ok",
                "n": n,
                "pearson_r": round(pearson, 4),
                "system_mean": round(mean_s, 2),
                "faculty_mean": round(mean_f, 2),
            }
        finally:
            db.close()

    except Exception as exc:
        log.exception("nightly_correlation failed: %s", exc)
        raise self.retry(exc=exc)


@celery_app.task(name="scheduled.retry_pending_neo4j_sync", bind=True, max_retries=0)
def retry_pending_neo4j_sync(self):
    """
    Every 15 min — re-attempt Neo4j sync for projects flagged pending_neo4j_sync
    (Postgres graph write succeeded, Neo4j write did not — see graph_builder.py).
    Stops early on the first GraphUnavailableError: if Neo4j is still down,
    every remaining row would fail identically, so there's no value in
    burning through the whole backlog on every 15-minute tick.
    """
    from app.database import SessionLocal
    from app.models.project import Project
    from app.services.graph_db import GRAPH_INGESTION_VERSION, GraphUnavailableError, graph_service

    db = SessionLocal()
    synced, still_pending, remaining = 0, 0, 0
    try:
        pending_projects = db.query(Project).filter(Project.pending_neo4j_sync.is_(True)).all()
        if not pending_projects:
            return {"status": "ok", "synced": 0, "still_pending": 0}

        log.info("retry_pending_neo4j_sync — %d project(s) pending", len(pending_projects))

        for i, project in enumerate(pending_projects):
            entities = project.extracted_entities or {}
            sub_domain = entities.get("sub_domain", "General")
            try:
                graph_service.build_project_graph(
                    project_id=str(project.id),
                    title=project.title,
                    domain=project.domain or "Unknown",
                    sub_domain=sub_domain or "Unknown",
                    extracted_entities=entities,
                    source_type="submission",
                    source_version=GRAPH_INGESTION_VERSION,
                )
                project.pending_neo4j_sync = False
                db.commit()
                synced += 1
            except GraphUnavailableError as exc:
                remaining = len(pending_projects) - i
                log.warning(
                    "retry_pending_neo4j_sync — Neo4j still unavailable (%s), "
                    "stopping this run with %d project(s) left pending", exc, remaining,
                )
                still_pending = remaining
                break
            except Exception as exc:
                log.exception("retry_pending_neo4j_sync — unexpected error for %s: %s", project.id, exc)
                still_pending += 1

        log.info("retry_pending_neo4j_sync done — synced=%d still_pending=%d", synced, still_pending)
        return {"status": "ok", "synced": synced, "still_pending": still_pending}
    finally:
        db.close()
