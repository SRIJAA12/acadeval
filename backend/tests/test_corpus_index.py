import pandas as pd
import pytest

from app.services.corpus_index import CorpusIndex

FIXTURE_ROWS = [
    # project_id, domain, sub_domain, algorithms, technologies, datasets, application
    ("P1", "AI", "Computer Vision", "CNN", "", "", "Attendance"),
    ("P2", "AI", "Computer Vision", "CNN", "", "", "Attendance"),
    ("P3", "AI", "Computer Vision", "ResNet", "", "", "Attendance"),
    ("P4", "AI", "NLP", "BERT", "", "", "Chatbot"),
]


@pytest.fixture
def fixture_index(tmp_path):
    csv_path = tmp_path / "fixture_corpus.csv"
    pd.DataFrame(FIXTURE_ROWS, columns=[
        "project_id", "domain", "sub_domain", "algorithms", "technologies", "datasets", "application",
    ]).to_csv(csv_path, index=False)
    return CorpusIndex(csv_path=str(csv_path))


def test_known_worked_example(fixture_index):
    # Candidate: AI / Computer Vision, algorithm ViT (never seen), application Attendance (seen 3x)
    result = fixture_index.compute_signals(
        domain="AI", subdomain="Computer Vision",
        algorithms=["ViT"], technologies=[], datasets=[], application="Attendance",
    )
    assert result["status"] == "ok"
    s = result["signals"]
    assert s["S1_nearest_project_distance"] == pytest.approx(0.6667, abs=1e-3)
    assert s["S2_feature_rarity"] == pytest.approx(0.625, abs=1e-3)
    assert s["S3_relationship_rarity"] == pytest.approx(1.0, abs=1e-3)
    assert s["S4_neighborhood_sparsity"] == pytest.approx(0.25, abs=1e-3)
    assert s["S5_new_connection_discovery"] == pytest.approx(1.0, abs=1e-3)
    assert result["flags"]["s5_all_entities_novel_to_corpus"] is True
    assert result["composite_score"] == pytest.approx(70.8, abs=0.1)
    assert result["band"] == "Moderately Novel"


def test_insufficient_historical_evidence(tmp_path):
    empty_csv = tmp_path / "empty.csv"
    pd.DataFrame(columns=["project_id", "domain", "sub_domain", "algorithms", "technologies", "datasets", "application"]).to_csv(empty_csv, index=False)
    index = CorpusIndex(csv_path=str(empty_csv))
    result = index.compute_signals(domain="AI", subdomain="CV", algorithms=["CNN"],
                                      technologies=[], datasets=[], application="X")
    assert result["status"] == "insufficient_historical_evidence"
    assert result["composite_score"] is None


def test_insufficient_extracted_evidence(fixture_index):
    result = fixture_index.compute_signals(domain="AI", subdomain="Computer Vision",
                                              algorithms=[], technologies=[], datasets=[], application=None)
    assert result["status"] == "insufficient_extracted_evidence"
    assert result["composite_score"] is None


def test_add_project_grows_corpus_immediately(fixture_index):
    before = fixture_index.n_projects
    fixture_index.add_project("P5", "AI", "Computer Vision", {"ALGO:vit", "APP:attendance"})
    assert fixture_index.n_projects == before + 1
    assert "P5" in fixture_index.projects
