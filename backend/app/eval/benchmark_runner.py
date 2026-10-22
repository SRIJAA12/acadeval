"""Runs the benchmark built by benchmark_builder.py against the current
scoring method (via LegacySnapshot — see that module for why) and writes
results as EvalMetric rows under one EvalRun.

Phase 0 scope, explicitly: the novelty engine has only one similarity
channel today (entity/graph overlap read from Neo4j), so every metric here
is tagged variant="graph_only". Metamorphic consistency, perturbation
sensitivity and S4 dispersion are NOT computed yet — they need the
canonicalizer (Phase 1) and the semantic channel (Phase 2) to be meaningful
rather than measuring known, already-understood bugs. Each metric is kept
separate; this module never combines them into one score.
"""
from __future__ import annotations

import logging
import time

from app.eval import metrics

log = logging.getLogger(__name__)

DUPLICATE_SIMILARITY_THRESHOLD = 0.5  # Phase-0 default; Phase 2 will tune this on the dev split


def _prefixed_corpus_id(project_id: str) -> str:
    """Neo4j corpus projects are stored as 'CORPUS-<id>' (backfill_corpus_graph.py);
    the benchmark's seed/foil ids come from the CSV catalog without that prefix."""
    return project_id if project_id.startswith("CORPUS-") else f"CORPUS-{project_id}"


def _run_synthetic_cases(snapshot, cases: list[dict]) -> list[dict]:
    from app.services.novelty_engine import NoveltyEngineService

    results = []
    for case in cases:
        q = case["query"]
        scored = snapshot.score(q["entities"], q["domain"], q["sub_domain"])
        relevant = {_prefixed_corpus_id(rid) for rid in case["relevant_ids"]}
        ranked_ids = [p["project_id"] for p in scored["similar_projects"]]
        top1 = scored["similar_projects"][0]["similarity_score"] if scored["similar_projects"] else 0.0
        results.append({
            "case_id": case["case_id"], "kind": case["kind"], "split": case["split"],
            "is_duplicate": case["is_duplicate"], "ranked_ids": ranked_ids, "relevant_ids": relevant,
            "top1_similarity": top1, "composite": scored["composite_novelty_score"],
        })
    return results


def _retrieval_metrics(results: list[dict]) -> dict:
    out = {}
    all_ranked = [r["ranked_ids"] for r in results]
    all_relevant = [r["relevant_ids"] for r in results]
    p1 = [metrics.precision_at_k(r, rel, 1) for r, rel in zip(all_ranked, all_relevant)]
    r5 = [metrics.recall_at_k(r, rel, 5) for r, rel in zip(all_ranked, all_relevant)]
    p1 = [v for v in p1 if v is not None]
    r5 = [v for v in r5 if v is not None]
    out["retrieval_p_at_1"] = metrics.bootstrap_ci(p1)
    out["retrieval_recall_at_5"] = metrics.bootstrap_ci(r5)
    mrr = metrics.mean_reciprocal_rank(all_ranked, all_relevant)
    out["retrieval_mrr"] = {"point": mrr, "ci_low": mrr, "ci_high": mrr, "n": len(results)}
    return out


def _duplicate_metrics(results: list[dict]) -> dict:
    y_true = [1 if r["is_duplicate"] else 0 for r in results]
    y_score = [r["top1_similarity"] for r in results]
    y_pred = [1 if s >= DUPLICATE_SIMILARITY_THRESHOLD else 0 for s in y_score]

    out = {"duplicate_detection": metrics.precision_recall_f1(y_true, y_pred)}
    out["duplicate_auc"] = metrics.auc_scores(y_true, y_score)
    return out


def _formula_correctness(db) -> dict:
    """Recomputes grade_for(overall_score) for every persisted EvaluationReport
    and checks it matches the stored grade — a cheap, always-available
    correctness check that needs no benchmark cases."""
    from app.models.evaluation import EvaluationReport
    from app.services.assessment_engine import grade_for

    rows = db.query(EvaluationReport.overall_score, EvaluationReport.grade).filter(
        EvaluationReport.overall_score.isnot(None)
    ).all()
    if not rows:
        return {"value": None, "n": 0, "details": {"reason": "no evaluation reports yet"}}
    correct = sum(1 for score, grade in rows if grade_for(score) == grade)
    return {"value": round(correct / len(rows), 4), "n": len(rows), "details": {"correct": correct}}


def _real_pairs_metrics(real_pairs: list[dict]) -> dict:
    """Entity-overlap-only similarity between the two abstracts/feature lists
    of each real pair (novelty_math.jaccard over the same label:name keys the
    live engine uses) — no semantic channel exists yet (Phase 2)."""
    from app.services.novelty_engine import _entity_key
    from app.services.novelty_math import jaccard

    if not real_pairs:
        return {}

    binary_pairs = [(p["binary_strict"], p) for p in real_pairs if p["binary_strict"] is not None]
    ordinal_pairs = [p for p in real_pairs if p["ordinal"] is not None]

    def _sim(pair: dict) -> float:
        a = {_entity_key("Technology", t) for t in pair["entities_a"].get("technologies", [])}
        b = {_entity_key("Technology", t) for t in pair["entities_b"].get("technologies", [])}
        return jaccard(a, b)

    out = {}
    if binary_pairs:
        y_true = [label for label, _ in binary_pairs]
        y_score = [_sim(p) for _, p in binary_pairs]
        out["real_pairs_auc_strict"] = {**metrics.auc_scores(y_true, y_score), "n": len(binary_pairs)}
    if ordinal_pairs:
        y_true = [p["ordinal"] for p in ordinal_pairs]
        y_score = [_sim(p) for p in ordinal_pairs]
        out["real_pairs_spearman"] = metrics.spearman_with_ties(y_score, y_true)
    return out


def run_benchmark(db, trigger: str, label: str | None = None):
    """Builds the benchmark, scores it, and writes one EvalRun + its
    EvalMetric rows. Returns the EvalRun object (already committed)."""
    from app.eval.benchmark_builder import build_benchmark
    from app.eval.legacy_scorer import LegacySnapshot
    from app.eval.versioning import compute_fingerprint, component_versions
    from app.models.quality import EvalRun, EvalMetric
    import uuid
    from datetime import datetime, timezone, timedelta

    t0 = time.monotonic()

    # Guard against overlapping runs (two triggers firing close together --
    # e.g. the worker-startup check and beat's first tick on a fresh schedule
    # -- or a Redis visibility-timeout redelivery of a still-running task).
    # A "running" row older than the task's own time limit is treated as
    # abandoned (its task was killed without updating the row) and ignored.
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=35)
    already_running = (
        db.query(EvalRun)
        .filter(EvalRun.kind == "benchmark", EvalRun.status == "running", EvalRun.started_at >= stale_cutoff)
        .first()
    )
    if already_running is not None:
        log.info("run_benchmark: another benchmark run (%s) is already in progress -- skipping", already_running.id)
        return already_running

    run = EvalRun(
        id=uuid.uuid4(), kind="benchmark", trigger=trigger, status="running",
        label=label, method_fingerprint=compute_fingerprint(), versions=component_versions(),
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()

    try:
        benchmark = build_benchmark()
        run.benchmark_version = benchmark["version"]
        run.n_cases = len(benchmark["synthetic_cases"]) + len(benchmark["real_pairs"])

        snapshot = LegacySnapshot.export()

        synthetic_results = _run_synthetic_cases(snapshot, benchmark["synthetic_cases"])
        holdout = [r for r in synthetic_results if r["split"] == "holdout"]

        metric_rows: list[EvalMetric] = []

        def add(metric_name: str, slice_name: str, value_dict: dict, target: float | None = None, target_op: str | None = None):
            value = value_dict.get("point", value_dict.get("value"))
            passed = None
            if target is not None and value is not None:
                passed = (value >= target) if target_op in (None, ">=") else (value <= target)
            metric_rows.append(EvalMetric(
                run_id=run.id, metric=metric_name, variant="graph_only", slice=slice_name,
                value=value, n=value_dict.get("n"), ci_low=value_dict.get("ci_low"), ci_high=value_dict.get("ci_high"),
                target=target, target_op=target_op, passed=passed,
                details={k: v for k, v in value_dict.items() if k not in ("point", "value", "n", "ci_low", "ci_high")},
            ))

        fc = _formula_correctness(db)
        add("formula_correctness_rate", "all", fc, target=1.0, target_op=">=")

        if holdout:
            for name, value in _retrieval_metrics(holdout).items():
                target = 0.90 if name == "retrieval_p_at_1" else (0.97 if name == "retrieval_recall_at_5" else None)
                add(name, "synthetic_holdout", value, target=target, target_op=">=")
            for name, value in _duplicate_metrics(holdout).items():
                if name == "duplicate_detection":
                    add("duplicate_precision", "synthetic_holdout", {"value": value.get("precision"), "n": len(holdout)}, target=0.95, target_op=">=")
                    add("duplicate_recall", "synthetic_holdout", {"value": value.get("recall"), "n": len(holdout)}, target=0.80, target_op=">=")
                    add("duplicate_f1", "synthetic_holdout", {"value": value.get("f1"), "n": len(holdout)})
                else:
                    add("duplicate_roc_auc", "synthetic_holdout", {"value": value.get("roc_auc"), "n": len(holdout)})
                    add("duplicate_pr_auc", "synthetic_holdout", {"value": value.get("pr_auc"), "n": len(holdout)})
        else:
            log.warning("run_benchmark: no holdout cases produced (corpus too small?)")

        for name, value in _real_pairs_metrics(benchmark["real_pairs"]).items():
            add(name, "simbench_real_pairs", {"value": value.get("roc_auc", value.get("rho")), "n": value.get("n")})

        add("real_pairs_excluded_conflicting", "simbench_real_pairs", {"value": float(len(benchmark["real_pairs_excluded_conflicting"])), "n": len(benchmark["real_pairs_excluded_conflicting"])})

        db.add_all(metric_rows)
        run.status = "ok"
    except Exception as exc:
        log.exception("run_benchmark failed")
        run.status = "failed"
        run.error = str(exc)[:2000]
    finally:
        run.finished_at = datetime.now(timezone.utc)
        run.duration_ms = round((time.monotonic() - t0) * 1000, 1)
        db.commit()

    return run
