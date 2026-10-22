"""Needs the real corpus CSV (datasets/new_dataset/...) and, for the real-pairs
loader, datasets/AcadEval_SimBench.csv -- both ship in the repo, so these run
without Docker. Skipped automatically if the files aren't where expected.
"""
import pytest

from app.eval.benchmark_builder import (
    build_synthetic_cases, load_real_pairs, benchmark_fingerprint, _project_hash_split,
)
from app.services.corpus_matcher import reset_corpus_cache, _resolve_corpus_paths


def _corpus_available() -> bool:
    try:
        return bool(_resolve_corpus_paths())
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _corpus_available(), reason="reference corpus CSV not found")


@pytest.fixture(autouse=True)
def _reset_cache():
    reset_corpus_cache()
    yield
    reset_corpus_cache()


def test_synthetic_cases_are_deterministic():
    cases_a = build_synthetic_cases(n_seeds=20, seed=42)
    reset_corpus_cache()
    cases_b = build_synthetic_cases(n_seeds=20, seed=42)
    assert [c["case_id"] for c in cases_a] == [c["case_id"] for c in cases_b]
    assert cases_a == cases_b


def test_synthetic_cases_cover_all_kinds():
    cases = build_synthetic_cases(n_seeds=10)
    kinds = {c["kind"] for c in cases}
    assert kinds == {"near_duplicate", "alias_variant", "hard_negative", "random_negative", "partial_splice"}


def test_near_duplicate_and_alias_variant_are_labelled_duplicate():
    cases = build_synthetic_cases(n_seeds=10)
    for c in cases:
        if c["kind"] in ("near_duplicate", "alias_variant"):
            assert c["is_duplicate"] is True
        else:
            assert c["is_duplicate"] is False


def test_every_case_has_dev_or_holdout_split():
    cases = build_synthetic_cases(n_seeds=10)
    assert all(c["split"] in ("dev", "holdout") for c in cases)


def test_project_hash_split_is_deterministic():
    assert _project_hash_split("P000123") == _project_hash_split("P000123")


def test_project_hash_split_covers_both_buckets():
    splits = {_project_hash_split(f"P{i:06d}") for i in range(200)}
    assert splits == {"dev", "holdout"}


def test_real_pairs_salvage_matches_investigation_numbers():
    result = load_real_pairs()
    # Hand-verified during investigation: 237 distinct pairs over SB00001-SB00987,
    # 8 excluded for conflicting labels within the same pair -> 229 usable.
    assert len(result["pairs"]) + len(result["conflicting_excluded"]) == pytest.approx(237, abs=1)
    assert len(result["conflicting_excluded"]) == pytest.approx(8, abs=1)
    for pair in result["pairs"]:
        assert pair["label"] in ("Different", "Partially Similar", "Partial Match", "Similar")
        assert "(Variant" not in pair["title_a"] and "(Ref" not in pair["title_a"]


def test_benchmark_fingerprint_changes_with_case_count():
    fp1 = benchmark_fingerprint([{"a": 1}], [])
    fp2 = benchmark_fingerprint([{"a": 1}, {"b": 2}], [])
    assert fp1 != fp2
