"""Tests for the real plagiarism checker (app/services/plagiarism_checker.py)
and its review-decision endpoint (app/routers/plagiarism.py)."""
import uuid

from app.models.project import SubmissionType
from app.models.user import UserRole
from app.services import plagiarism_checker
from tests.conftest import make_user, auth_headers
from tests.test_rbac import make_project

SHARED_PARAGRAPH = (
    "This project implements a federated learning pipeline for crop disease "
    "detection using convolutional neural networks trained directly on edge "
    "devices without ever uploading raw images to a central server for privacy "
    "reasons, which matters most for farmers in low-connectivity rural regions "
    "who still need fast, reliable, and locally computed diagnostic feedback."
)
# Deliberately NOT a shared sentence template with words swapped (that would
# reproduce the exact templated-text false-positive problem this checker is
# built to avoid — confirmed in the real reference corpus CSV).
FILLER_A = (
    "Mango orchards across the valley suffered an early frost this harvest "
    "season and farmers are negotiating new insurance premiums with regional "
    "cooperatives before the next planting cycle begins in spring. "
) * 3
FILLER_B = (
    "City council members debated a proposal to repaint the downtown bridge "
    "and extend weekend parking permits near the riverside market after "
    "residents complained about congestion during the summer festival. "
) * 3


def _make_full_project(db_session, student, parsed_text, **kwargs):
    project = make_project(db_session, student, **kwargs)
    project.submission_type = SubmissionType.document
    project.parsed_text = parsed_text
    db_session.commit()
    db_session.refresh(project)
    return project


def _add_match(db_session, project, score=0.7):
    from app.models.plagiarism import PlagiarismMatch, MatchType
    match = PlagiarismMatch(
        id=uuid.uuid4(), project_id=project.id, match_type=MatchType.text,
        source_project_id=None, source_label="Some other project",
        candidate_passage="x" * 50, source_passage="x" * 50, score=score,
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    return match


# ── Passage splitting ─────────────────────────────────────────────────────────

def test_split_passages_prefers_paragraphs():
    text = f"Short line.\n\n{SHARED_PARAGRAPH}\n\n{FILLER_A}"
    passages = plagiarism_checker.split_passages(text, min_words=10)
    assert any(SHARED_PARAGRAPH[:20] in p for p, _ in passages)
    assert all(loc.startswith("paragraph") for _, loc in passages)


def test_split_passages_sliding_window_fallback():
    text = " ".join(["word"] * 150)  # no paragraph breaks at all
    passages = plagiarism_checker.split_passages(text, min_words=10)
    assert len(passages) > 1
    assert all(loc.startswith("words") for _, loc in passages)


def test_split_passages_empty_text():
    assert plagiarism_checker.split_passages("") == []
    assert plagiarism_checker.split_passages(None) == []


# ── Code winnowing ────────────────────────────────────────────────────────────

def test_winnowing_detects_near_identical_code():
    code = "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n" * 3
    fp_a = plagiarism_checker._fingerprint_files([{"path": "a.py", "content": code}])
    fp_b = plagiarism_checker._fingerprint_files([{"path": "b.py", "content": code}])
    union = fp_a | fp_b
    jaccard = len(fp_a & fp_b) / len(union) if union else 0.0
    assert jaccard > 0.9


def test_winnowing_distinguishes_different_code():
    code_a = "def add(a, b):\n    return a + b\n" * 10
    code_b = "class Matrix:\n    def __init__(self, n):\n        self.n = n\n" * 10
    fp_a = plagiarism_checker._fingerprint_files([{"path": "a.py", "content": code_a}])
    fp_b = plagiarism_checker._fingerprint_files([{"path": "b.py", "content": code_b}])
    assert len(fp_a & fp_b) == 0


def test_winnowing_ignores_comments():
    code_with_comments = "# this is a header comment\ndef add(a, b):\n    # add two numbers\n    return a + b\n" * 5
    code_without = "def add(a, b):\n    return a + b\n" * 5
    fp_a = plagiarism_checker._fingerprint_files([{"path": "a.py", "content": code_with_comments}])
    fp_b = plagiarism_checker._fingerprint_files([{"path": "b.py", "content": code_without}])
    union = fp_a | fp_b
    jaccard = len(fp_a & fp_b) / len(union) if union else 0.0
    assert jaccard > 0.8


# ── Text similarity (DB-backed) ──────────────────────────────────────────────

def test_text_similarity_finds_planted_overlap(client, db_session):
    student_a = make_user(db_session, UserRole.student)
    student_b = make_user(db_session, UserRole.student)
    project_a = _make_full_project(db_session, student_a, parsed_text=f"{SHARED_PARAGRAPH}\n\n{FILLER_A}")
    project_b = _make_full_project(db_session, student_b, parsed_text=f"{FILLER_B}\n\n{SHARED_PARAGRAPH}")

    summary = plagiarism_checker.run_plagiarism_check(project_a, db_session)
    assert summary["text_match_count"] >= 1
    assert summary["text_max"] > 0.5
    assert summary["code_match_count"] == 0  # no github_url set

    from app.models.plagiarism import PlagiarismMatch
    match = db_session.query(PlagiarismMatch).filter(PlagiarismMatch.project_id == project_a.id).first()
    assert match is not None
    assert match.source_project_id == project_b.id
    assert SHARED_PARAGRAPH[:20] in match.candidate_passage


def test_unrelated_projects_produce_no_match(client, db_session):
    student_a = make_user(db_session, UserRole.student)
    student_b = make_user(db_session, UserRole.student)
    project_a = _make_full_project(db_session, student_a, parsed_text=FILLER_A)
    _make_full_project(db_session, student_b, parsed_text=FILLER_B)

    summary = plagiarism_checker.run_plagiarism_check(project_a, db_session)
    assert summary["text_match_count"] == 0
    assert summary["text_max"] == 0.0


def test_rerun_preserves_reviewed_matches(client, db_session):
    student_a = make_user(db_session, UserRole.student)
    student_b = make_user(db_session, UserRole.student)
    project_a = _make_full_project(db_session, student_a, parsed_text=f"{SHARED_PARAGRAPH}\n\n{FILLER_A}")
    _make_full_project(db_session, student_b, parsed_text=f"{FILLER_B}\n\n{SHARED_PARAGRAPH}")

    plagiarism_checker.run_plagiarism_check(project_a, db_session)

    from app.models.plagiarism import PlagiarismMatch, ReviewStatus
    match = db_session.query(PlagiarismMatch).filter(PlagiarismMatch.project_id == project_a.id).first()
    match.review_status = ReviewStatus.confirmed
    match.reviewer_comment = "Confirmed copied intro paragraph."
    db_session.commit()

    plagiarism_checker.run_plagiarism_check(project_a, db_session)  # rerun, nothing changed

    still_there = db_session.query(PlagiarismMatch).filter(
        PlagiarismMatch.project_id == project_a.id, PlagiarismMatch.review_status == ReviewStatus.confirmed,
    ).first()
    assert still_there is not None
    assert still_there.reviewer_comment == "Confirmed copied intro paragraph."


# ── Plagiarism report endpoint ────────────────────────────────────────────────

def test_student_can_view_own_plagiarism_report(client, db_session):
    student = make_user(db_session, UserRole.student)
    project = make_project(db_session, student)
    resp = client.get(f"/api/projects/{project.id}/plagiarism-report", headers=auth_headers(student))
    assert resp.status_code == 200
    body = resp.json()
    assert body["matches"] == []
    assert "No significant match" in body["summaryText"]


def test_outsider_student_cannot_view_report(client, db_session):
    student = make_user(db_session, UserRole.student)
    outsider = make_user(db_session, UserRole.student)
    project = make_project(db_session, student)
    resp = client.get(f"/api/projects/{project.id}/plagiarism-report", headers=auth_headers(outsider))
    assert resp.status_code == 403


# ── Review-decision permissions ───────────────────────────────────────────────

def test_guide_can_review_match(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide)  # guide_submitted=True by default
    match = _add_match(db_session, project)

    resp = client.patch(
        f"/api/plagiarism-matches/{match.id}/review",
        json={"reviewStatus": "acceptable_overlap", "reviewerComment": "Shared boilerplate template."},
        headers=auth_headers(guide),
    )
    assert resp.status_code == 200
    assert resp.json()["reviewStatus"] == "acceptable_overlap"
    assert resp.json()["reviewerComment"] == "Shared boilerplate template."


def test_student_cannot_review_match(client, db_session):
    student = make_user(db_session, UserRole.student)
    project = make_project(db_session, student)
    match = _add_match(db_session, project)

    resp = client.patch(f"/api/plagiarism-matches/{match.id}/review",
                         json={"reviewStatus": "no_issue"}, headers=auth_headers(student))
    assert resp.status_code == 403


def test_coordinator_cannot_review_match(client, db_session):
    student = make_user(db_session, UserRole.student)
    coordinator = make_user(db_session, UserRole.coordinator)
    project = make_project(db_session, student)
    match = _add_match(db_session, project)

    resp = client.patch(f"/api/plagiarism-matches/{match.id}/review",
                         json={"reviewStatus": "no_issue"}, headers=auth_headers(coordinator))
    assert resp.status_code == 403


def test_outsider_guide_cannot_review_match(client, db_session):
    student = make_user(db_session, UserRole.student)
    assigned_guide = make_user(db_session, UserRole.guide)
    outsider_guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=assigned_guide)
    match = _add_match(db_session, project)

    resp = client.patch(f"/api/plagiarism-matches/{match.id}/review",
                         json={"reviewStatus": "no_issue"}, headers=auth_headers(outsider_guide))
    assert resp.status_code == 403


def test_review_rejects_invalid_status(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide)
    match = _add_match(db_session, project)

    resp = client.patch(f"/api/plagiarism-matches/{match.id}/review",
                         json={"reviewStatus": "unreviewed"}, headers=auth_headers(guide))
    assert resp.status_code == 422
