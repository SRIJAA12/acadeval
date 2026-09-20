"""
Module 11 — Celery Pipeline Tasks
===================================
Each task wraps one step of the AcadEval+ pipeline.  They are chained via
Celery's chain() primitive so the submission endpoint stays non-blocking.

Chain order:
  task_parse_and_classify  →  task_extract_entities
    →  task_score_and_report  →  task_ingest_graph  →  task_finalise

The candidate is scored before graph ingestion so it cannot affect its own
rarity, density, connection, or nearest-project evidence.

Every task receives the project_id (str) as its only argument so tasks can be
individually retried without re-running upstream steps.
"""

from __future__ import annotations

import logging
from pathlib import Path

from celery import chain as celery_chain
from celery.utils.log import get_task_logger

from app.worker import celery_app

log = get_task_logger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_db():
    from app.database import SessionLocal
    return SessionLocal()


def _load_project(db, project_id: str):
    from app.models.project import Project
    import uuid
    return db.query(Project).filter(Project.id == uuid.UUID(project_id)).first()


# ── Task 1: Document parsing + domain classification ─────────────────────────

@celery_app.task(
    bind=True, name="pipeline.parse_and_classify",
    max_retries=2, default_retry_delay=10,
    acks_late=True,
)
def task_parse_and_classify(self, project_id: str) -> str:
    """
    Step 1 — Document Ingestion & Module 1 (Domain Classification).
    Parses every uploaded file attached to the project, extracts raw text,
    then classifies domain/sub-domain and writes results to the DB row.
    Returns project_id so the next task in the chain receives it.
    """
    db = _get_db()
    try:
        from app.models.project import PipelineStatus
        from app.services.document_parser import document_parser_service
        from app.services.classifier import classifier_service

        project = _load_project(db, project_id)
        if not project:
            log.error("parse_and_classify: project %s not found", project_id)
            return project_id

        project.pipeline_status = PipelineStatus.ai_processing
        db.commit()

        # ── Parse uploaded files ──────────────────────────────────────────────
        extracted_text = ""
        parsed_title = ""
        parsed_abstract = ""

        for pf in project.files:
            if pf.storage_path and Path(pf.storage_path).exists():
                try:
                    parsed = document_parser_service.parse_uploaded_file(
                        file_path=pf.storage_path,
                        filename=pf.original_filename,
                    )
                    struct = parsed.get("parsed_structure", {})
                    if struct.get("title") and not parsed_title:
                        parsed_title = struct["title"]
                    if struct.get("abstract"):
                        parsed_abstract += "\n" + struct["abstract"]
                    extracted_text += "\n" + parsed.get("raw_text", "")
                except Exception as exc:
                    log.warning("File parse failed (%s): %s", pf.original_filename, exc)

        # ── GitHub feature extraction ─────────────────────────────────────────
        if project.github_url:
            try:
                gh = document_parser_service.fetch_github_features(project.github_url)
                extracted_text += "\n" + gh.get("raw_text", "")
            except Exception as exc:
                log.warning("GitHub extraction skipped: %s", exc)

        if parsed_title and (not project.title or "Uploaded Project" in project.title):
            project.title = parsed_title

        effective_abstract = (
            project.abstract or parsed_abstract or extracted_text[:2000] or project.title
        ).strip()

        # ── Module 1: Classify ────────────────────────────────────────────────
        sub_domain = ""
        try:
            cls_res = classifier_service.classify_project(project.title, effective_abstract)
            if cls_res.get("domain"):
                project.domain = cls_res["domain"]
            sub_domain = cls_res.get("sub_domain", "")
        except Exception as exc:
            log.warning("Module 1 classification skipped: %s", exc)

        project.abstract = effective_abstract
        project.parsed_text = extracted_text.strip() or None
        project.extracted_entities = {
            "_effective_abstract": effective_abstract,
            "_sub_domain": sub_domain,
        }
        db.commit()

        log.info("parse_and_classify done for %s", project_id)
        return project_id

    except Exception as exc:
        db.rollback()
        log.exception("parse_and_classify failed for %s: %s", project_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


# ── Task 2: Entity extraction ─────────────────────────────────────────────────

@celery_app.task(
    bind=True, name="pipeline.extract_entities",
    max_retries=2, default_retry_delay=15,
    acks_late=True,
)
def task_extract_entities(self, project_id: str) -> str:
    """
    Step 2 — Module 2 (Entity Extraction).
    Reads the effective_abstract stored by Task 1, runs NLP entity extraction,
    and writes the structured entity dict back to project.extracted_entities.
    """
    db = _get_db()
    try:
        from app.services.extractor import extractor_service

        project = _load_project(db, project_id)
        if not project:
            return project_id

        cached = project.extracted_entities or {}
        abstract = project.abstract or cached.get("_effective_abstract", project.title)

        entities = extractor_service.extract_from_full_proposal(
            title=project.title, abstract=abstract
        )
        if cached.get("_sub_domain"):
            entities["sub_domain"] = cached["_sub_domain"]
        # Merge with cache (keep _effective_abstract for downstream tasks)
        entities["_effective_abstract"] = abstract
        project.extracted_entities = entities
        db.commit()

        log.info("extract_entities done for %s — %d entity categories",
                 project_id, len(entities) - 1)
        return project_id

    except Exception as exc:
        db.rollback()
        log.exception("extract_entities failed for %s: %s", project_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


# ── Task 4: Post-score graph ingestion ───────────────────────────────────────

@celery_app.task(
    bind=True, name="pipeline.ingest_graph",
    max_retries=3, default_retry_delay=20,
    acks_late=True,
)
def task_ingest_graph(self, project_id: str) -> str:
    """
    Step 4 — Graph Construction after scoring.
    Writes the project and its entities only after a versioned novelty report
    has been persisted.
    """
    db = _get_db()
    try:
        from datetime import datetime, timezone
        from app.services.graph_builder import ingest_project_to_relational_graph
        from app.services.graph_db import GRAPH_INGESTION_VERSION

        project = _load_project(db, project_id)
        if not project:
            return project_id

        entities = project.extracted_entities or {}
        sub_domain = entities.get("sub_domain", "General")

        if not project.evaluation or not project.evaluation.novelty_report:
            raise RuntimeError("Refusing graph ingestion before novelty evidence is persisted")

        ingest_project_to_relational_graph(
            db=db,
            project_id=str(project.id),
            title=project.title,
            domain=project.domain or "General CSE",
            sub_domain=sub_domain,
            extracted_entities=entities,
        )

        project.graph_ingested_at = datetime.now(timezone.utc)
        project.graph_ingestion_version = GRAPH_INGESTION_VERSION
        db.commit()

        log.info("ingest_graph done for %s", project_id)
        return project_id

    except Exception as exc:
        db.rollback()
        log.exception("ingest_graph failed for %s: %s", project_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


# ── Task 3: Frozen-snapshot novelty scoring + report assembly ─────────────────

@celery_app.task(
    bind=True, name="pipeline.score_and_report",
    max_retries=2, default_retry_delay=15,
    acks_late=True,
)
def task_score_and_report(self, project_id: str) -> str:
    """
    Step 3 — Modules 5 & 6 (Novelty Scoring + Report Assembly).
    Runs the novelty engine and trend scorer, then persists the composite
    score onto the EvaluationReport row so the frontend can display it.
    """
    db = _get_db()
    try:
        from datetime import datetime, timezone
        from app.models.evaluation import EvaluationReport
        from app.services.novelty_engine import (
            SCORING_METHOD_VERSION,
            novelty_engine_service,
        )
        from app.services.trend_scorer import trend_scorer_service
        from app.services.classifier import classifier_service

        project = _load_project(db, project_id)
        if not project:
            return project_id

        entities = project.extracted_entities or {}
        abstract = entities.get("_effective_abstract", project.title)
        domain = project.domain or "General CSE"
        sub_domain = entities.get("sub_domain", "General")

        input_hash = novelty_engine_service.input_hash(
            project.title,
            domain,
            sub_domain,
            entities,
        )
        eval_report = (
            db.query(EvaluationReport)
            .filter(EvaluationReport.project_id == project.id)
            .first()
        )
        if (
            eval_report
            and eval_report.novelty_report
            and eval_report.novelty_method_version == SCORING_METHOD_VERSION
            and eval_report.novelty_input_hash == input_hash
        ):
            log.info("score_and_report reused persisted v2 evidence for %s", project_id)
            return project_id

        # Module 5 — Novelty signals. Failure must be visible to Celery/API;
        # a fabricated score would invalidate both the product and the paper.
        novelty = novelty_engine_service.compute_novelty_signals(
            project_id=str(project.id),
            extracted_entities=entities,
            domain=domain,
            sub_domain=sub_domain,
        )

        # Module 5 — Trend scoring
        try:
            cls_res = classifier_service.classify_project(project.title, abstract)
            topic = cls_res.get("topic", domain)
            trend = trend_scorer_service.get_topic_trend(topic)
        except Exception as exc:
            log.warning("Trend scoring unavailable for %s: %s", project_id, exc)
            trend = {
                "topic": domain,
                "growth_rate_pct": None,
                "paper_count_3yr": None,
                "citation_velocity": None,
                "trend_status": "Unavailable",
                "data_source": "unavailable",
            }

        # Module 6 — Citation & Reference Analysis
        citation_analysis = {}
        try:
            from app.services.citation_analyzer import citation_analysis_service
            # Identify first PDF file attached if any
            first_pdf = next(
                (pf.storage_path for pf in project.files if pf.storage_path and pf.storage_path.lower().endswith(".pdf")),
                None
            )
            citation_analysis = citation_analysis_service.analyze_references(
                file_path=first_pdf,
                raw_text=abstract
            )
        except Exception as exc:
            log.warning("Module 6 Citation analysis skipped (%s)", exc)
            citation_analysis = {"summary": {}, "flags": [], "references": []}

        # Module 7 — Writing Quality Analysis
        writing_analysis = {}
        try:
            from app.services.writing_analyzer import writing_quality_service
            writing_analysis = writing_quality_service.analyze_text(abstract)
        except Exception as exc:
            log.warning("Module 7 Writing Quality analysis skipped (%s)", exc)
            writing_analysis = {"overall_rating": "N/A", "metrics": {}, "flags": []}

        # Persist onto EvaluationReport
        BAND_TO_VERDICT = {
            "Highly Novel": "Novel",
            "Moderately Novel": "Somewhat Novel",
            "Low Novelty / Incremental": "Common",
            "Insufficient Historical Evidence": "Insufficient Evidence",
            "Insufficient Extracted Evidence": "Insufficient Evidence",
        }

        if eval_report is None:
            eval_report = EvaluationReport(project_id=project.id)
            db.add(eval_report)

        score = novelty["composite_novelty_score"]
        band = novelty["novelty_band"]

        eval_report.novelty_score = score
        eval_report.novelty_verdict = BAND_TO_VERDICT.get(band, "Somewhat Novel")
        # Novelty is one dimension, not a substitute for the overall rubric.
        # Keep the overall result pending until the remaining engines run.
        if not eval_report.grade:
            eval_report.grade = "N/A"

        eval_report.novelty_report = {
            "project_id": str(project.id),
            "title": project.title,
            "domain": domain,
            "sub_domain": sub_domain,
            "overall_novelty_band": band,
            "overall_novelty_score": score,
            "signals_breakdown": {
                "graph_distance": novelty["signal_1_graph_distance"],
                "feature_rarity": novelty["signal_2_feature_rarity"],
                "relationship_rarity": novelty["signal_3_relationship_rarity"],
                "graph_density": novelty["signal_4_graph_density"],
                "new_connection_discovery": novelty["signal_5_new_connection_discovery"],
            },
            "extracted_entities": {
                key: value for key, value in entities.items() if not key.startswith("_")
            },
            "trend_context": trend,
            "most_similar_projects": novelty["similar_projects"],
            "explanation_lines": novelty["explanation_bullets"],
            "scoring_metadata": novelty["scoring_metadata"],
        }
        metadata = novelty["scoring_metadata"]
        eval_report.novelty_method_version = metadata["method_version"]
        eval_report.novelty_corpus_version = metadata["corpus_snapshot_id"]
        eval_report.novelty_corpus_size = metadata["corpus_project_count"]
        eval_report.novelty_input_hash = input_hash
        eval_report.novelty_scored_at = datetime.now(timezone.utc)

        signal_findings = [
            ("Distinct from the nearest historical project", novelty["signal_1_graph_distance"]),
            ("Uses uncommon technical features", novelty["signal_2_feature_rarity"]),
            ("Combines features that rarely co-occur", novelty["signal_3_relationship_rarity"]),
            ("Targets a relatively sparse graph neighborhood", novelty["signal_4_graph_density"]),
            ("Creates previously unseen connections between known features", novelty["signal_5_new_connection_discovery"]),
        ]
        eval_report.strengths = [label for label, value in signal_findings if value >= 0.65]
        eval_report.weaknesses = [label for label, value in signal_findings if value < 0.35]

        # Attach Module 6 citations sub-scores and flags to EvaluationReport
        eval_report.citations = citation_analysis
        if citation_analysis.get("flags"):
            eval_report.flagging_reasons = list(set((eval_report.flagging_reasons or []) + citation_analysis["flags"]))

        # Attach Module 7 writing quality analysis to EvaluationReport
        eval_report.writing_quality = writing_analysis
        if writing_analysis.get("flags"):
            eval_report.flagging_reasons = list(set((eval_report.flagging_reasons or []) + writing_analysis["flags"]))

        # Build dynamic improvement roadmap based on project's actual findings
        dyn_roadmap = []

        # Week 1: Domain & Missing Section / Baseline focus
        w1_actions = [f"Compare baseline results against SOTA benchmarks in {domain}"]
        if citation_analysis.get("flags"):
            w1_actions.append("Address bibliography quality flags: " + citation_analysis["flags"][0])
        else:
            w1_actions.append("Expand literature review with 3-5 recent open-access papers")

        dyn_roadmap.append({
            "week": 1,
            "focus": f"Literature & Baselines in {domain}",
            "actions": w1_actions
        })

        # Week 2: Technical Architecture & Feature Verification
        algos = entities.get("algorithms", [])
        algo_name = algos[0] if algos else "core model"
        w2_actions = [f"Conduct ablation study on {algo_name} architecture"]
        if writing_analysis.get("flags"):
            w2_actions.append("Refine document tone: " + writing_analysis["flags"][0])
        else:
            w2_actions.append("Formalize mathematical and architectural parameter definitions")

        dyn_roadmap.append({
            "week": 2,
            "focus": f"Ablation Studies & {algo_name.title()} Refinement",
            "actions": w2_actions
        })

        # Week 3: Final Documentation & Deployment
        techs = entities.get("technologies", []) + entities.get("frameworks", [])
        tech_name = techs[0] if techs else "system"
        dyn_roadmap.append({
            "week": 3,
            "focus": f"System Integration & {tech_name.title()} Deployment",
            "actions": [
                f"Containerize {tech_name} pipeline for reproducible evaluation",
                "Finalize code repository documentation and license"
            ]
        })

        eval_report.improvement_roadmap = dyn_roadmap
        eval_report.badges = eval_report.badges or ["Processed by AcadEval+"]

        db.commit()

        log.info("score_and_report done for %s — score=%.1f band=%s",
                 project_id, score, band)
        return project_id

    except Exception as exc:
        db.rollback()
        log.exception("score_and_report failed for %s: %s", project_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


# ── Task 5: Mark pipeline complete ───────────────────────────────────────────

@celery_app.task(
    bind=True, name="pipeline.finalise",
    max_retries=1, default_retry_delay=5,
    acks_late=True,
)
def task_finalise(self, project_id: str) -> dict:
    """
    Step 5 — Mark pipeline complete.
    Sets pipeline_status to awaiting_review and cleans up the temp abstract
    key from extracted_entities.
    """
    db = _get_db()
    try:
        from app.models.project import PipelineStatus

        project = _load_project(db, project_id)
        if not project:
            return {"project_id": project_id, "status": "not_found"}

        # Strip internal scratch key before saving
        if project.extracted_entities and "_effective_abstract" in project.extracted_entities:
            cleaned = dict(project.extracted_entities)
            cleaned.pop("_effective_abstract", None)
            project.extracted_entities = cleaned

        project.pipeline_status = PipelineStatus.awaiting_review
        db.commit()

        # ── Module 14: Send Email Notifications ──────────────────────────────
        try:
            from app.services.notification_service import notify_report_ready, notify_faculty_review_needed, notify_proposal_flagged
            student = project.student
            eval_rep = project.evaluation

            if student and student.email:
                score_val = eval_rep.overall_score if eval_rep else 0.0
                grade_val = eval_rep.grade if eval_rep else "N/A"
                notify_report_ready(
                    student_email=student.email,
                    student_name=student.name,
                    project_title=project.title,
                    overall_score=score_val,
                    grade=grade_val,
                    project_id=str(project.id),
                )

            guide = project.assigned_guide
            if guide and guide.email:
                notify_faculty_review_needed(
                    guide_email=guide.email,
                    guide_name=guide.name,
                    student_name=student.name if student else "Student",
                    project_title=project.title,
                    project_id=str(project.id),
                )

            # Send critical alert if proposal was flagged
            if eval_rep and eval_rep.flagging_reasons:
                notify_target = (guide.email if guide else None) or student.email
                if notify_target:
                    notify_proposal_flagged(
                        hod_email=notify_target,
                        hod_name="Faculty Reviewer",
                        project_title=project.title,
                        student_name=student.name if student else "Student",
                        flags=eval_rep.flagging_reasons,
                        project_id=str(project.id),
                    )
        except Exception as exc:
            log.warning("Module 14 email notification failed (%s)", exc)

        log.info("Pipeline COMPLETE for project %s", project_id)
        return {"project_id": project_id, "status": "complete"}

    except Exception as exc:
        db.rollback()
        log.exception("finalise failed for %s: %s", project_id, exc)
        raise self.retry(exc=exc)
    finally:
        db.close()


# ── Public helper: build and dispatch the full chain ─────────────────────────

def enqueue_pipeline(project_id: str):
    """
    Builds and dispatches the full 5-step pipeline chain for a project.
    Returns the AsyncResult of the first task (use result.id as the job_id
    to poll via GET /projects/{project_id}/pipeline-status).
    """
    pipeline = celery_chain(
        task_parse_and_classify.s(project_id),
        task_extract_entities.s(),
        task_score_and_report.s(),
        task_ingest_graph.s(),
        task_finalise.s(),
    )
    result = pipeline.apply_async()
    log.info("Enqueued pipeline for project %s — chain id=%s", project_id, result.id)
    return result
