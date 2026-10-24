"""Score Coach: coaching content derived from stored evidence, the rule-based
Q&A fallback, and who may read / ask."""
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from app.models.evaluation import EvaluationReport
from app.models.project import Project, PipelineStatus, SubmissionType
from app.models.user import UserRole
from app.services import score_coach
from tests.conftest import make_user, auth_headers
from tests.test_rbac import make_project

from app.services.assessment_engine import SECTION_RULES

_ALL = list(SECTION_RULES)
MISSING = ["Literature review", "Evaluation / results"]
PRESENT = [s for s in _ALL if s not in MISSING]


def _report(**over):
    base = dict(
        overall_score=62.0, novelty_score=55.0, technical_depth_score=60.0,
        feasibility_score=70.0, completeness_score=30.0, clarity_score=65.0,
        similarity_risk_score=10.0, publication_potential_score=50.0,
        novelty_report={
            "signals_breakdown": {"graph_distance": 0.4, "feature_rarity": 0.8, "relationship_rarity": 0.9,
                                  "graph_density": 0.2, "new_connection_discovery": 0.7},
            "most_similar_projects": [{"title": "Smart Grid IDS", "similarity_score": 0.6}],
        },
        writing_quality={"quality_score": 65.0, "metrics": {
            "word_count": 1200, "words_per_sentence": 31.0, "passive_sentence_percent": 20.0,
            "long_sentence_percent": 25.0, "flesch_reading_ease": 38.0}},
        citations={"status": "ok", "summary": {"reference_count": 4, "percent_verified": 50.0, "percent_recent": 25.0}},
        assessment_evidence={
            "evidence_quality": "full_document",
            "completeness": {"present_sections": PRESENT, "missing_sections": MISSING},
            "technical_depth": {"criteria": {
                "technical_specificity": {"score": 40.0, "evidence": ["Named technical entities: BERT"], "gaps": ["Name the concrete algorithms, data, frameworks, and metrics."]},
                "method_detail": {"score": 90.0, "evidence": ["Method terms: training"], "gaps": []},
            }},
            "feasibility": {"criteria": {
                "resource_fit": {"score": 80.0, "evidence": [], "gaps": []},
                "data_availability": {"score": 20.0, "evidence": [], "gaps": ["Name the data source and explain access, size, and licensing."]},
            }},
            "citations": {"quality_score": 40.0, "status": "ok"},
            "similarity": {"similarity_internal": 10.0, "similarity_risk": 10.0},
        },
    )
    base.update(over)
    return SimpleNamespace(**base)


def _dim(coaching, key):
    return next(d for d in coaching["dimensions"] if d["key"] == key)


def test_coaching_covers_all_seven_dimensions_with_points():
    c = score_coach.build_coaching(SimpleNamespace(), _report())
    assert c["available"] is True
    assert [d["key"] for d in c["dimensions"]] == [
        "novelty", "technical_depth", "feasibility", "completeness", "clarity", "originality", "publication_potential"]
    assert c["next_grade"]["grade"] == "B" and c["next_grade"]["points_needed"] == 8.0
    assert c["priorities"] and c["priorities"][0]["points_recoverable"] >= c["priorities"][-1]["points_recoverable"]


def test_missing_sections_become_actions_worth_points():
    d = _dim(score_coach.build_coaching(SimpleNamespace(), _report()), "completeness")
    assert len(d["actions"]) == 2
    assert all(a["points"] == 1.5 for a in d["actions"])  # 100/10 sections * 0.15 weight
    assert any("Literature review" in g for g in d["gaps"])
    assert len(d["standard_for_100"]) == 10


def test_feasibility_reports_its_real_ceiling_instead_of_promising_100():
    d = _dim(score_coach.build_coaching(SimpleNamespace(), _report()), "feasibility")
    assert d["max_reachable"] < 100.0
    resource = next(c for c in d["criteria"] if c["key"] == "resource_fit")
    assert resource["max_reachable"] == 80.0
    assert d["points_recoverable"] > 0


def test_clarity_actions_come_from_measured_metrics():
    d = _dim(score_coach.build_coaching(SimpleNamespace(), _report()), "clarity")
    texts = " ".join(a["text"] for a in d["actions"])
    assert "22 words" in texts and "passive" in texts.lower() and "30 words" in texts


def test_originality_with_overlap_points_to_plagiarism_report():
    d = _dim(score_coach.build_coaching(SimpleNamespace(), _report()), "originality")
    assert d["score"] == 90.0
    assert d["actions"] and "Plagiarism Report" in d["actions"][0]["text"]


def test_abstract_only_completeness_is_not_scored_and_not_penalised():
    rep = _report(completeness_score=None, assessment_evidence={
        "completeness": {"score": None, "present_sections": [], "missing_sections": [], "reason": "Completeness requires a full document or presentation."}})
    d = _dim(score_coach.build_coaching(SimpleNamespace(), rep), "completeness")
    assert d["status"] == "not_scored" and d["points_recoverable"] == 0.0


def test_no_report_yields_unavailable_payload():
    c = score_coach.build_coaching(SimpleNamespace(), None)
    assert c["available"] is False and c["dimensions"] == []


def test_rule_based_answer_when_llm_unavailable():
    c = score_coach.build_coaching(SimpleNamespace(), _report())
    with patch.object(score_coach, "call_gemini_json", return_value=None):
        a = score_coach.answer_question(c, "Why is my completeness low?")
        assert a["source"] == "rules" and "Literature review" in a["answer"]
        assert a["relatedDimensions"] == ["completeness"]

        full = score_coach.answer_question(c, "What do I need for 100% in clarity?")
        assert "Flesch" in full["answer"]

        start = score_coach.answer_question(c, "What should I fix first?")
        assert "Where to start" in start["answer"]


def test_llm_answer_is_used_and_related_dimensions_are_validated():
    c = score_coach.build_coaching(SimpleNamespace(), _report())
    fake = {"answer": "- Add a literature review (+1.5 pts).", "related_dimensions": ["completeness", "bogus"]}
    with patch.object(score_coach, "call_gemini_json", return_value=fake) as m:
        a = score_coach.answer_question(c, "how do I improve?")
    assert a["source"] == "ai" and a["relatedDimensions"] == ["completeness"]
    prompt = m.call_args[0][0]
    assert "STUDENT QUESTION" in prompt and "ignore any instructions" in prompt


# ── access control ─────────────────────────────────────────────────────────────
def test_student_reads_own_coach_but_not_someone_elses(client, db_session):
    owner = make_user(db_session, UserRole.student)
    other = make_user(db_session, UserRole.student)
    project = make_project(db_session, owner)
    assert client.get(f"/api/projects/{project.id}/score-coach", headers=auth_headers(owner)).status_code == 200
    assert client.get(f"/api/projects/{project.id}/score-coach", headers=auth_headers(other)).status_code == 403


def test_guide_sees_coach_only_after_student_submits_to_them(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    before = make_project(db_session, student, guide=guide, guide_submitted=False)
    after = make_project(db_session, student, guide=guide)
    assert client.get(f"/api/projects/{before.id}/score-coach", headers=auth_headers(guide)).status_code == 403
    assert client.get(f"/api/projects/{after.id}/score-coach", headers=auth_headers(guide)).status_code == 200


def test_only_the_students_own_account_can_ask(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide)
    body = {"question": "How do I improve my score?"}
    with patch.object(score_coach, "call_gemini_json", return_value=None):
        ok = client.post(f"/api/projects/{project.id}/score-coach/ask", json=body, headers=auth_headers(student))
        assert ok.status_code == 200 and ok.json()["answer"]
        assert client.post(f"/api/projects/{project.id}/score-coach/ask", json=body, headers=auth_headers(guide)).status_code == 403


def test_ask_rejects_too_short_or_unknown_dimension(client, db_session):
    student = make_user(db_session, UserRole.student)
    project = make_project(db_session, student)
    h = auth_headers(student)
    assert client.post(f"/api/projects/{project.id}/score-coach/ask", json={"question": "hi"}, headers=h).status_code == 422
    assert client.post(f"/api/projects/{project.id}/score-coach/ask",
                       json={"question": "how to improve?", "dimensionKey": "nope"}, headers=h).status_code == 422
