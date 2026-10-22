"""Correlation between AcadEval's system score and real faculty ratings —
the one metric that touches actual ground truth. Reported separately per
method_fingerprint so a method change doesn't silently mix old and new scores
into one misleading number, and never collapsed with any other metric.

Deliberately uses the system_score SNAPSHOT stored on FacultyEvaluation at
review time (not the live, possibly-overridden-since EvaluationReport.novelty_score
that the old nightly_correlation task read) — see models/evaluation.py.
"""
from __future__ import annotations

from app.eval import metrics


def compute_faculty_agreement(db, min_n: int = 10) -> dict:
    """Returns {metric_name: {"value", "n", "ci_low", "ci_high", "details"}}
    grouped by method_fingerprint. Groups with fewer than min_n rows are
    still returned (n is always reported) but flagged `below_min_n` so the
    dashboard can grey them out rather than hide them silently.
    """
    from app.models.evaluation import FacultyEvaluation

    rows = (
        db.query(FacultyEvaluation.faculty_score, FacultyEvaluation.system_score, FacultyEvaluation.method_fingerprint)
        .filter(FacultyEvaluation.faculty_score.isnot(None), FacultyEvaluation.system_score.isnot(None))
        .all()
    )

    groups: dict[str, list[tuple[float, float]]] = {}
    for faculty_score, system_score, fingerprint in rows:
        key = fingerprint or "unknown"
        groups.setdefault(key, []).append((float(faculty_score), float(system_score) / 10.0))

    out: dict[str, dict] = {}
    for fingerprint, pairs in groups.items():
        faculty = [p[0] for p in pairs]
        system = [p[1] for p in pairs]
        n = len(pairs)
        below_min = n < min_n

        pear = metrics.pearson(system, faculty)
        spear = metrics.spearman_with_ties(system, faculty)
        kend = metrics.kendall_tau(system, faculty)
        mae_val = metrics.mae(system, faculty)

        suffix = f":{fingerprint}"
        out[f"faculty_agreement_pearson{suffix}"] = {"value": pear["r"], "n": n, "details": {"p_value": pear["p_value"], "below_min_n": below_min}}
        out[f"faculty_agreement_spearman{suffix}"] = {"value": spear["rho"], "n": n, "details": {"p_value": spear["p_value"], "below_min_n": below_min}}
        out[f"faculty_agreement_kendall{suffix}"] = {"value": kend["tau"], "n": n, "details": {"p_value": kend["p_value"], "below_min_n": below_min}}
        out[f"faculty_agreement_mae{suffix}"] = {"value": mae_val, "n": n, "details": {"below_min_n": below_min}}

    if not groups:
        out["faculty_agreement_pearson:none"] = {"value": None, "n": 0, "details": {"reason": "no faculty evaluations yet"}}

    return out
