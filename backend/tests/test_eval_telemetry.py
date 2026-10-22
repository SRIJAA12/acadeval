from types import SimpleNamespace

from app.eval.telemetry import _check_invariants, _explanation_coverage, FORBIDDEN_EXPLANATION_PHRASES


def _report(**kwargs):
    defaults = dict(
        overall_score=72.0, novelty_score=65.0, grade="B",
        feasibility_score=80.0, completeness_score=70.0, technical_depth_score=60.0,
        clarity_score=75.0, similarity_risk_score=20.0, publication_potential_score=55.0,
        is_duplicate=False,
        novelty_report={"signals_breakdown": {"graph_distance": 0.6, "feature_rarity": 0.4}},
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_invariants_all_pass_on_a_healthy_report():
    checks = _check_invariants(_report(), {})
    assert all(checks.values()), checks


def test_invariant_catches_out_of_range_score():
    checks = _check_invariants(_report(overall_score=150.0), {})
    assert checks["overall_score_in_range"] is False


def test_invariant_catches_nan_score():
    checks = _check_invariants(_report(overall_score=float("nan")), {})
    assert checks["overall_score_in_range"] is False


def test_invariant_catches_signal_out_of_range():
    checks = _check_invariants(
        _report(novelty_report={"signals_breakdown": {"graph_distance": 1.5}}), {}
    )
    assert checks["signals_in_range"] is False


def test_invariant_catches_grade_score_mismatch():
    # grade_for(72) should be "B" (>=70), not "A+"
    checks = _check_invariants(_report(overall_score=72.0, grade="A+"), {})
    assert checks["grade_matches_score"] is False


def test_invariant_grade_matches_when_consistent():
    checks = _check_invariants(_report(overall_score=72.0, grade="B"), {})
    assert checks["grade_matches_score"] is True


def test_invariant_catches_duplicate_flagged_with_low_risk():
    checks = _check_invariants(_report(is_duplicate=True, similarity_risk_score=10.0), {})
    assert checks["duplicate_flag_consistent"] is False


def test_invariant_none_scores_do_not_fail():
    checks = _check_invariants(_report(novelty_score=None), {})
    assert checks["novelty_score_in_range"] is True


def test_explanation_coverage_counts_claims_and_backing():
    novelty_report = {"explanation_lines": [
        "The candidate shares no rare entities with prior work.",
        "Scored using Adamic-Adar index and SimBench calibration.",
        "Nearest match found in the corpus with moderate overlap.",
    ]}
    claims, backed, forbidden = _explanation_coverage(novelty_report)
    assert claims == 3
    assert forbidden == 1
    assert backed == 2


def test_explanation_coverage_empty_report():
    assert _explanation_coverage({}) == (0, 0, 0)
    assert _explanation_coverage(None) == (0, 0, 0)


def test_forbidden_phrases_list_is_nonempty():
    # guards against someone accidentally clearing the list and silently
    # making forbidden_claims always 0
    assert len(FORBIDDEN_EXPLANATION_PHRASES) > 0
