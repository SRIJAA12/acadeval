"""The method fingerprint: one short hash identifying "what scoring logic and
what data would score a submission right now". When it changes — a formula
edit, a corpus reload, a model bump — old telemetry/benchmark rows stay
attributed to the old fingerprint, and app/tasks/evaluation.py's
check_versions task notices the change and runs the benchmark automatically.

This is a fingerprint, not a semantic version: no ordering is implied between
two different hashes, only equality/inequality.
"""
from __future__ import annotations

import hashlib
import json


def _novelty_version() -> str:
    from app.services.novelty_engine import SCORING_METHOD_VERSION
    return SCORING_METHOD_VERSION


def _assessment_version() -> str:
    from app.services.assessment_engine import ASSESSMENT_METHOD_VERSION
    return ASSESSMENT_METHOD_VERSION


def _matcher_version() -> str:
    from app.services.corpus_matcher import SIMILARITY_METHOD_VERSION
    return SIMILARITY_METHOD_VERSION


def _corpus_fingerprint() -> str:
    from app.services.corpus_matcher import get_corpus_fingerprint
    try:
        return get_corpus_fingerprint()
    except Exception:
        return "unavailable"


def _embedding_model_id() -> str:
    try:
        from app.services.embeddings import EMBEDDING_MODEL_ID
        return EMBEDDING_MODEL_ID
    except ImportError:
        return "none"  # Phase 0: semantic channel not added yet


def component_versions() -> dict:
    """The individual version/fingerprint strings that make up the method
    fingerprint — stored alongside it (scoring_telemetry.versions,
    eval_runs.versions) so a dashboard can show *which* component changed.
    """
    return {
        "novelty": _novelty_version(),
        "assessment": _assessment_version(),
        "matcher": _matcher_version(),
        "corpus": _corpus_fingerprint(),
        "embedding_model": _embedding_model_id(),
    }


def compute_fingerprint() -> str:
    versions = component_versions()
    blob = json.dumps(versions, sort_keys=True).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]
