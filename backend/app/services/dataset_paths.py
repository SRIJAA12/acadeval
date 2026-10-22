"""Single source of truth for resolving files under the project's `datasets/`
folder. Replaces the half-dozen near-identical directory-search snippets that
used to be duplicated across corpus_matcher.py, extractor.py, routers/entities.py,
classifier.py, and backend/app/eval/benchmark_builder.py (each with its own
list of candidate directories, including a stale hardcoded `D:/acadeval-1`
path from a previous checkout location).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def _dataset_root_candidates() -> list[Path]:
    """Directories that might be the project's `datasets/` folder, in
    priority order: the Docker-mounted path, the current working directory,
    then walking up from this file's own location (works regardless of
    whether the app runs in Docker or directly on a host checkout)."""
    candidates = [Path("/datasets"), Path("./datasets")]
    for parent in Path(__file__).resolve().parents:
        candidates.append(parent / "datasets")
    return candidates


def resolve_dataset_dir(*relative: str) -> Path:
    """Resolves a subdirectory under `datasets/` (e.g. `resolve_dataset_dir("taxonomy")`).
    Returns the first candidate that exists on disk, or the first candidate
    (even if missing) so callers get a stable, loggable path to report in errors."""
    rel = Path(*relative) if relative else Path(".")
    first = None
    for root in _dataset_root_candidates():
        candidate = root / rel
        if first is None:
            first = candidate
        if candidate.exists():
            return candidate
    return first if first is not None else rel


def resolve_dataset_file(*relative: str) -> Optional[Path]:
    """Resolves a file under `datasets/` (e.g. `resolve_dataset_file("corpus", "AcadEval_Corpus_MASTER.csv")`).
    Returns None if no candidate root has that file — callers decide how to
    handle a missing dataset (log + degrade, raise, etc.) rather than this
    helper silently returning a path that doesn't exist."""
    rel = Path(*relative)
    for root in _dataset_root_candidates():
        candidate = root / rel
        if candidate.exists():
            return candidate
    return None
