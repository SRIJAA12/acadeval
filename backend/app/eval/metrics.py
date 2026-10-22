"""Generic statistics used by the benchmark runner and faculty-agreement check.
Thin wrappers over scipy/sklearn/numpy (already dependencies) plus a bootstrap
confidence interval helper, since none of scipy/sklearn ship one directly.

Every function returns plain Python floats/ints (JSON-serialisable) and
tolerates degenerate input (n<2, all-same values) by returning None rather
than raising, since this runs unattended on a schedule.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy import stats
from sklearn.metrics import average_precision_score, roc_auc_score


def safe_float(x) -> float | None:
    try:
        v = float(x)
        return None if math.isnan(v) or math.isinf(v) else v
    except (TypeError, ValueError):
        return None


def precision_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int) -> float | None:
    """Share of the top-k retrieved ids that are relevant."""
    top_k = ranked_ids[:k]
    if not top_k:
        return None
    return sum(1 for i in top_k if i in relevant_ids) / len(top_k)


def recall_at_k(ranked_ids: Sequence[str], relevant_ids: set[str], k: int) -> float | None:
    if not relevant_ids:
        return None
    found = sum(1 for i in ranked_ids[:k] if i in relevant_ids)
    return found / len(relevant_ids)


def reciprocal_rank(ranked_ids: Sequence[str], relevant_ids: set[str]) -> float:
    for rank, item_id in enumerate(ranked_ids, start=1):
        if item_id in relevant_ids:
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(all_ranked: Sequence[Sequence[str]], all_relevant: Sequence[set[str]]) -> float | None:
    if not all_ranked:
        return None
    return float(np.mean([reciprocal_rank(r, rel) for r, rel in zip(all_ranked, all_relevant)]))


def precision_recall_f1(y_true: Sequence[int], y_pred: Sequence[int]) -> dict:
    """Binary precision/recall/F1 (y_true/y_pred are 0/1)."""
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * precision * recall / (precision + recall)) if (precision and recall and (precision + recall) > 0) else None
    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def auc_scores(y_true: Sequence[int], y_score: Sequence[float]) -> dict:
    """ROC-AUC and PR-AUC. None if y_true has only one class (undefined)."""
    y_true = np.asarray(y_true)
    if len(set(y_true.tolist())) < 2:
        return {"roc_auc": None, "pr_auc": None}
    return {
        "roc_auc": safe_float(roc_auc_score(y_true, y_score)),
        "pr_auc": safe_float(average_precision_score(y_true, y_score)),
    }


def spearman_with_ties(x: Sequence[float], y: Sequence[float]) -> dict:
    """scipy already average-ranks ties by default — this wrapper exists so
    callers don't have to remember that (the old hand-rolled Spearman in
    acadeval_plus.py did not handle ties)."""
    if len(x) < 2:
        return {"rho": None, "p_value": None, "n": len(x)}
    rho, p = stats.spearmanr(x, y)
    return {"rho": safe_float(rho), "p_value": safe_float(p), "n": len(x)}


def kendall_tau(x: Sequence[float], y: Sequence[float]) -> dict:
    if len(x) < 2:
        return {"tau": None, "p_value": None, "n": len(x)}
    tau, p = stats.kendalltau(x, y, variant="b")
    return {"tau": safe_float(tau), "p_value": safe_float(p), "n": len(x)}


def pearson(x: Sequence[float], y: Sequence[float]) -> dict:
    if len(x) < 2 or np.std(x) == 0 or np.std(y) == 0:
        return {"r": None, "p_value": None, "n": len(x)}
    r, p = stats.pearsonr(x, y)
    return {"r": safe_float(r), "p_value": safe_float(p), "n": len(x)}


def mae(x: Sequence[float], y: Sequence[float]) -> float | None:
    if not x:
        return None
    return float(np.mean(np.abs(np.asarray(x) - np.asarray(y))))


def bootstrap_ci(values: Sequence[float], statistic=np.mean, n_resamples: int = 2000, confidence: float = 0.95, seed: int = 42) -> dict:
    """95% CI by resampling `values` with replacement. Used wherever a metric
    is reported without an analytic CI (precision, recall, mean deltas, ...)."""
    values = np.asarray([v for v in values if v is not None], dtype=float)
    if len(values) < 2:
        point = safe_float(statistic(values)) if len(values) else None
        return {"point": point, "ci_low": point, "ci_high": point, "n": len(values)}
    rng = np.random.default_rng(seed)
    resamples = rng.choice(values, size=(n_resamples, len(values)), replace=True)
    stat_values = statistic(resamples, axis=1) if statistic is np.mean else np.array([statistic(r) for r in resamples])
    alpha = (1 - confidence) / 2
    lo, hi = np.quantile(stat_values, [alpha, 1 - alpha])
    return {
        "point": safe_float(statistic(values)),
        "ci_low": safe_float(lo),
        "ci_high": safe_float(hi),
        "n": len(values),
    }
