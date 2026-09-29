"""
Verifies the Neo4j -> in-memory-corpus fallback in
NoveltyEngineService.compute_novelty_signals (app/services/novelty_engine.py).

Note on shape: this asserts the REAL production return contract
(novelty_band / composite_novelty_score / signal_1_graph_distance / ...),
which is what app/tasks/pipeline.py and app/services/report_generator.py
already read from this method today -- not the corpus_index.py-native
contract (status / composite_score / signals{...}) that
test_corpus_index.py checks. Those are two different, deliberately-kept-
separate contracts; see the novelty-engine fix report for why.
"""
import pytest

from app.config import settings
from app.services.graph_db import GraphUnavailableError, ProjectGraphService
from app.services.novelty_engine import novelty_engine_service

SAMPLE_CANDIDATE = {
    "algorithms": ["CNN"],
    "technologies": ["TensorFlow"],
    "frameworks": [],
    "libraries": [],
    "datasets": ["PlantVillage"],
    "applications": ["crop disease detection"],
    "hardware": [],
    "metrics": [],
}


@pytest.fixture
def force_neo4j_unavailable(monkeypatch):
    def _raise(self):
        raise GraphUnavailableError("simulated outage")
    # session() is a @contextmanager; patching it to raise before yielding
    # reproduces exactly what a real Neo4j outage looks like to callers.
    monkeypatch.setattr(ProjectGraphService, "session", _raise)


@pytest.fixture
def auto_backend(monkeypatch):
    """auto mode is required to actually exercise the fallback path -- the
    default "corpus" mode never touches Neo4j at all, so a simulated outage
    there would prove nothing."""
    monkeypatch.setattr(settings, "NOVELTY_GRAPH_BACKEND", "auto")


def test_fallback_on_graph_unavailable(force_neo4j_unavailable, auto_backend):
    result = novelty_engine_service.compute_novelty_signals(
        project_id="TEST-fallback-0001",
        extracted_entities=SAMPLE_CANDIDATE,
        domain="Artificial Intelligence",
        sub_domain="Machine Learning",
    )

    assert result["scoring_metadata"]["graph_backend"] == "in-memory-corpus"
    assert result["novelty_band"] in (
        "Highly Novel", "Moderately Novel", "Low Novelty / Incremental",
        "Insufficient Historical Evidence", "Insufficient Extracted Evidence",
    )
    assert 0 <= result["composite_novelty_score"] <= 100
    # Never a bare crash, and never None masquerading as a real score.
    for key in (
        "signal_1_graph_distance", "signal_2_feature_rarity", "signal_3_relationship_rarity",
        "signal_4_graph_density", "signal_5_new_connection_discovery",
    ):
        assert isinstance(result[key], float)


def test_strict_neo4j_mode_reraises(force_neo4j_unavailable, monkeypatch):
    monkeypatch.setattr(settings, "NOVELTY_GRAPH_BACKEND", "neo4j")
    with pytest.raises(GraphUnavailableError):
        novelty_engine_service.compute_novelty_signals(
            project_id="TEST-fallback-0002",
            extracted_entities=SAMPLE_CANDIDATE,
            domain="Artificial Intelligence",
            sub_domain="Machine Learning",
        )


def test_corpus_mode_never_touches_neo4j(force_neo4j_unavailable, monkeypatch):
    """Default mode: Neo4j being down (or even broken) must not matter at all."""
    monkeypatch.setattr(settings, "NOVELTY_GRAPH_BACKEND", "corpus")
    result = novelty_engine_service.compute_novelty_signals(
        project_id="TEST-fallback-0003",
        extracted_entities=SAMPLE_CANDIDATE,
        domain="Artificial Intelligence",
        sub_domain="Machine Learning",
    )
    assert result["scoring_metadata"]["graph_backend"] == "in-memory-corpus"
    assert 0 <= result["composite_novelty_score"] <= 100
