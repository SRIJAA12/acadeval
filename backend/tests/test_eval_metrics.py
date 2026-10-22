import math

import pytest

from app.eval import metrics


def test_precision_recall_f1():
    r = metrics.precision_recall_f1([1, 0, 1, 1], [1, 0, 0, 1])
    assert r["precision"] == 1.0
    assert math.isclose(r["recall"], 2 / 3)
    assert r["tp"] == 2 and r["fp"] == 0 and r["fn"] == 1


def test_precision_recall_f1_handles_all_negative():
    r = metrics.precision_recall_f1([0, 0], [0, 0])
    assert r["precision"] is None  # no positive predictions
    assert r["recall"] is None     # no actual positives


def test_auc_scores_undefined_for_single_class():
    r = metrics.auc_scores([1, 1, 1], [0.2, 0.5, 0.9])
    assert r["roc_auc"] is None
    assert r["pr_auc"] is None


def test_auc_scores_perfect_separation():
    r = metrics.auc_scores([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9])
    assert r["roc_auc"] == 1.0


def test_spearman_with_ties_does_not_crash_on_ties():
    # [1,2,2,4] has a tie -- the old hand-rolled Spearman in acadeval_plus.py
    # did not handle ties; this wrapper must.
    r = metrics.spearman_with_ties([1, 2, 2, 4], [1, 2, 3, 4])
    assert r["rho"] is not None
    assert r["n"] == 4


def test_spearman_single_point_returns_none():
    r = metrics.spearman_with_ties([1], [1])
    assert r["rho"] is None


def test_kendall_tau_perfect_agreement():
    r = metrics.kendall_tau([1, 2, 3, 4], [1, 2, 3, 4])
    assert r["tau"] == 1.0


def test_pearson_constant_input_returns_none():
    r = metrics.pearson([5, 5, 5], [1, 2, 3])
    assert r["r"] is None


def test_mae():
    assert metrics.mae([1, 2, 3], [1, 2, 5]) == pytest.approx(2 / 3)


def test_bootstrap_ci_degenerate_single_value():
    r = metrics.bootstrap_ci([0.5])
    assert r["point"] == 0.5
    assert r["n"] == 1


def test_bootstrap_ci_empty_returns_none_point():
    r = metrics.bootstrap_ci([])
    assert r["point"] is None
    assert r["n"] == 0


def test_bootstrap_ci_is_reproducible():
    vals = [0.1, 0.3, 0.5, 0.7, 0.9, 0.2, 0.4]
    r1 = metrics.bootstrap_ci(vals)
    r2 = metrics.bootstrap_ci(vals)
    assert r1 == r2


def test_safe_float_rejects_nan_and_inf():
    assert metrics.safe_float(float("nan")) is None
    assert metrics.safe_float(float("inf")) is None
    assert metrics.safe_float("abc") is None
    assert metrics.safe_float("1.5") == 1.5
