"""API-level RBAC / assignment-scoping tests.

Closes the gap flagged during the Person-2 audit: previously any guide or
reviewer could score, publish, or read the internal report of ANY project
just by knowing its id, because only role was checked, never assignment.
These tests exercise the real FastAPI app + a real (transaction-rolled-back)
Postgres session, so they catch the actual wiring, not just the helper
function in isolation.
"""
import uuid
from datetime import datetime, timezone

import pytest

from app.models.project import Project, PipelineStatus, SubmissionType
from app.models.evaluation import EvaluationReport
from app.models.user import UserRole
from tests.conftest import make_user, auth_headers


def make_project(db_session, student, guide=None, reviewer=None, **kwargs) -> Project:
    # guide_submitted defaults to True whenever a guide is passed, so every
    # existing test that assumes "assignment = access" keeps working — tests
    # for the pre-submission gate itself pass guide_submitted=False explicitly.
    guide_submitted = kwargs.get("guide_submitted", guide is not None)
    project = Project(
        id=uuid.uuid4(),
        student_id=student.id,
        title=kwargs.get("title", "Test Project"),
        domain=kwargs.get("domain", "AI/ML"),
        submission_type=SubmissionType.abstract,
        pipeline_status=kwargs.get("pipeline_status", PipelineStatus.awaiting_review),
        assigned_guide_id=guide.id if guide else None,
        assigned_reviewer_id=reviewer.id if reviewer else None,
        guide_submitted_at=datetime.now(timezone.utc) if guide_submitted else None,
        is_preliminary=kwargs.get("is_preliminary", True),
    )
    db_session.add(project)
    db_session.flush()
    db_session.add(EvaluationReport(
        project_id=project.id, overall_score=72.0, grade="B",
        novelty_score=70.0, feasibility_score=75.0,
    ))
    db_session.commit()
    db_session.refresh(project)
    return project


# ── Faculty actions require assignment, not just role ──────────────────────────
# Publish/override-score are reviewer+HOD only — the guide's own marks are
# informal (guide_feedback.py) and never touch the official record.

def test_guide_cannot_publish_even_when_assigned(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide)

    resp = client.post(f"/api/projects/{project.id}/publish", headers=auth_headers(guide))
    assert resp.status_code == 403


def test_unassigned_reviewer_cannot_publish(client, db_session):
    student = make_user(db_session, UserRole.student)
    other_reviewer = make_user(db_session, UserRole.reviewer)
    outsider_reviewer = make_user(db_session, UserRole.reviewer)
    project = make_project(db_session, student, reviewer=other_reviewer)

    resp = client.post(f"/api/projects/{project.id}/publish", headers=auth_headers(outsider_reviewer))
    assert resp.status_code == 403


def test_assigned_reviewer_can_publish(client, db_session):
    student = make_user(db_session, UserRole.student)
    reviewer = make_user(db_session, UserRole.reviewer)
    project = make_project(db_session, student, reviewer=reviewer)

    resp = client.post(f"/api/projects/{project.id}/publish", headers=auth_headers(reviewer))
    assert resp.status_code == 200


def test_unassigned_reviewer_cannot_override_score(client, db_session):
    student = make_user(db_session, UserRole.student)
    assigned_reviewer = make_user(db_session, UserRole.reviewer)
    outsider_reviewer = make_user(db_session, UserRole.reviewer)
    project = make_project(db_session, student, reviewer=assigned_reviewer)

    resp = client.patch(
        f"/api/projects/{project.id}/scores",
        json={"dimension": "novelty", "newValue": 90.0, "comment": "test"},
        headers=auth_headers(outsider_reviewer),
    )
    assert resp.status_code == 403


def test_unassigned_faculty_cannot_read_internal_report(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    outsider = make_user(db_session, UserRole.reviewer)
    project = make_project(db_session, student, guide=guide)

    resp = client.get(f"/api/projects/{project.id}/report/internal", headers=auth_headers(outsider))
    assert resp.status_code == 403


def test_hod_bypasses_assignment(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    hod = make_user(db_session, UserRole.hod)
    project = make_project(db_session, student, guide=guide)

    resp = client.get(f"/api/projects/{project.id}/report/internal", headers=auth_headers(hod))
    assert resp.status_code == 200


def test_unassigned_project_invisible_to_other_faculty(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    other_guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide)

    resp = client.get("/api/projects", headers=auth_headers(other_guide))
    assert resp.status_code == 200
    ids = {p["projectId"] for p in resp.json()}
    assert str(project.id) not in ids

    resp_owner = client.get("/api/projects", headers=auth_headers(guide))
    ids_owner = {p["projectId"] for p in resp_owner.json()}
    assert str(project.id) in ids_owner


# ── Role-only endpoints still reject the wrong role entirely ───────────────────

def test_student_cannot_list_all_projects(client, db_session):
    student = make_user(db_session, UserRole.student)
    resp = client.get("/api/projects", headers=auth_headers(student))
    assert resp.status_code == 403


def test_non_hod_cannot_assign_projects(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student)

    resp = client.patch(
        f"/api/projects/{project.id}/assign",
        json={"guideId": str(guide.id)},
        headers=auth_headers(guide),
    )
    assert resp.status_code == 403


def test_hod_can_assign_and_assignment_grants_access(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    hod = make_user(db_session, UserRole.hod)
    project = make_project(db_session, student)

    # Before assignment: guide has no access.
    resp = client.get(f"/api/projects/{project.id}/report/internal", headers=auth_headers(guide))
    assert resp.status_code == 403

    resp = client.patch(
        f"/api/projects/{project.id}/assign",
        json={"guideId": str(guide.id)},
        headers=auth_headers(hod),
    )
    assert resp.status_code == 200
    assert resp.json()["guideName"] == guide.name

    # Assignment alone is no longer enough — the student must submit to the
    # guide before the guide can see anything (see test_rbac submit-to-guide
    # gate tests below).
    resp = client.get(f"/api/projects/{project.id}/report/internal", headers=auth_headers(guide))
    assert resp.status_code == 403

    resp = client.patch(f"/api/projects/{project.id}/submit-to-guide", headers=auth_headers(student))
    assert resp.status_code == 200

    resp = client.get(f"/api/projects/{project.id}/report/internal", headers=auth_headers(guide))
    assert resp.status_code == 200


# ── Submit-to-Guide / Ready-for-Review gating ───────────────────────────────────

def test_guide_cannot_see_project_until_submitted(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide, guide_submitted=False)

    resp = client.get("/api/projects", headers=auth_headers(guide))
    assert resp.status_code == 200
    assert str(project.id) not in {p["projectId"] for p in resp.json()}

    resp = client.get(f"/api/projects/{project.id}/report/internal", headers=auth_headers(guide))
    assert resp.status_code == 403

    resp = client.get(f"/api/projects/{project.id}/discussion", headers=auth_headers(guide))
    assert resp.status_code == 403

    resp = client.put(f"/api/projects/{project.id}/guide-feedback",
                       json={"overallScore": 65.0, "comment": "x"}, headers=auth_headers(guide))
    assert resp.status_code == 403


def test_submit_to_guide_requires_score_above_30(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide, guide_submitted=False)
    project.evaluation.overall_score = 25.0
    db_session.commit()

    resp = client.patch(f"/api/projects/{project.id}/submit-to-guide", headers=auth_headers(student))
    assert resp.status_code == 422


def test_submit_to_guide_requires_a_guide(client, db_session):
    student = make_user(db_session, UserRole.student)
    project = make_project(db_session, student)  # no guide assigned

    resp = client.patch(f"/api/projects/{project.id}/submit-to-guide", headers=auth_headers(student))
    assert resp.status_code == 422


def test_submit_to_guide_opens_access(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide, guide_submitted=False)

    resp = client.get(f"/api/projects/{project.id}/report/internal", headers=auth_headers(guide))
    assert resp.status_code == 403

    resp = client.patch(f"/api/projects/{project.id}/submit-to-guide", headers=auth_headers(student))
    assert resp.status_code == 200
    assert resp.json()["guideSubmittedAt"] is not None

    resp = client.get(f"/api/projects/{project.id}/report/internal", headers=auth_headers(guide))
    assert resp.status_code == 200


def test_other_student_cannot_submit_to_guide(client, db_session):
    student = make_user(db_session, UserRole.student)
    outsider = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide, guide_submitted=False)

    resp = client.patch(f"/api/projects/{project.id}/submit-to-guide", headers=auth_headers(outsider))
    assert resp.status_code == 404


def test_mark_ready_for_review_requires_score_above_30(client, db_session):
    student = make_user(db_session, UserRole.student)
    project = make_project(db_session, student)
    project.evaluation.overall_score = 10.0
    db_session.commit()

    resp = client.patch(f"/api/projects/{project.id}/mark-ready-for-review", headers=auth_headers(student))
    assert resp.status_code == 422


def test_mark_ready_for_review_succeeds(client, db_session):
    student = make_user(db_session, UserRole.student)
    project = make_project(db_session, student)

    resp = client.patch(f"/api/projects/{project.id}/mark-ready-for-review", headers=auth_headers(student))
    assert resp.status_code == 200
    assert resp.json()["reviewerReadyAt"] is not None


def test_assign_rejects_mismatched_role(client, db_session):
    student = make_user(db_session, UserRole.student)
    hod = make_user(db_session, UserRole.hod)
    not_a_guide = make_user(db_session, UserRole.reviewer)
    project = make_project(db_session, student)

    resp = client.patch(
        f"/api/projects/{project.id}/assign",
        json={"guideId": str(not_a_guide.id)},
        headers=auth_headers(hod),
    )
    assert resp.status_code == 422


def test_guide_cannot_create_rubric(client, db_session):
    guide = make_user(db_session, UserRole.guide)
    resp = client.post(
        "/api/rubrics",
        json={"name": "Test Rubric", "department": "CSE", "criteria": []},
        headers=auth_headers(guide),
    )
    assert resp.status_code == 403


def test_non_hod_cannot_approve_rubric(client, db_session):
    coordinator = make_user(db_session, UserRole.coordinator)
    guide = make_user(db_session, UserRole.guide)
    resp = client.post(
        "/api/rubrics",
        json={"name": "Test Rubric", "department": "CSE", "criteria": []},
        headers=auth_headers(coordinator),
    )
    assert resp.status_code == 201
    rubric_id = resp.json()["rubricId"]

    resp = client.patch(f"/api/rubrics/{rubric_id}/approve", headers=auth_headers(guide))
    assert resp.status_code == 403


def test_non_hod_cannot_view_audit_logs(client, db_session):
    guide = make_user(db_session, UserRole.guide)
    resp = client.get("/api/audit-logs", headers=auth_headers(guide))
    assert resp.status_code == 403


def test_hod_can_view_audit_logs(client, db_session):
    hod = make_user(db_session, UserRole.hod)
    resp = client.get("/api/audit-logs", headers=auth_headers(hod))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── Student report visibility ───────────────────────────────────────────────────

def test_student_cannot_read_another_students_report(client, db_session):
    owner = make_user(db_session, UserRole.student)
    other_student = make_user(db_session, UserRole.student)
    project = make_project(db_session, owner)

    resp = client.get(f"/api/projects/{project.id}/report/public", headers=auth_headers(other_student))
    assert resp.status_code == 403


def test_preliminary_report_shows_score_and_weaknesses_immediately(client, db_session):
    """The whole point of the preliminary-score fix: a student should see
    their AI score and weaknesses before faculty publish, not a blank
    skeleton."""
    student = make_user(db_session, UserRole.student)
    project = make_project(db_session, student, is_preliminary=True,
                            pipeline_status=PipelineStatus.awaiting_review)

    resp = client.get(f"/api/projects/{project.id}/report/public", headers=auth_headers(student))
    assert resp.status_code == 200
    body = resp.json()
    assert body["isPreliminary"] is True
    assert body["overallScore"] == 72.0
    assert body["dimensionScores"]["novelty"] == 70.0


# ── Discussion forum: guide + student only, reviewer excluded ──────────────────

def test_assigned_reviewer_cannot_read_discussion(client, db_session):
    student = make_user(db_session, UserRole.student)
    reviewer = make_user(db_session, UserRole.reviewer)
    project = make_project(db_session, student, reviewer=reviewer)

    resp = client.get(f"/api/projects/{project.id}/discussion", headers=auth_headers(reviewer))
    assert resp.status_code == 403


def test_assigned_guide_can_use_discussion(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide)

    resp = client.post(f"/api/projects/{project.id}/discussion", json={"body": "hello"}, headers=auth_headers(guide))
    assert resp.status_code == 201

    resp = client.get(f"/api/projects/{project.id}/discussion", headers=auth_headers(student))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["body"] == "hello"


def test_outsider_guide_cannot_use_discussion(client, db_session):
    student = make_user(db_session, UserRole.student)
    assigned_guide = make_user(db_session, UserRole.guide)
    outsider_guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=assigned_guide)

    resp = client.get(f"/api/projects/{project.id}/discussion", headers=auth_headers(outsider_guide))
    assert resp.status_code == 403


# ── Progress updates: append-only, student-authored ─────────────────────────────

def test_student_can_post_progress_update(client, db_session):
    student = make_user(db_session, UserRole.student)
    project = make_project(db_session, student)

    resp = client.post(f"/api/projects/{project.id}/progress", data={"content": "Finished the literature review."},
                        headers=auth_headers(student))
    assert resp.status_code == 201
    assert resp.json()["content"] == "Finished the literature review."


def test_non_owner_student_cannot_post_progress(client, db_session):
    owner = make_user(db_session, UserRole.student)
    other_student = make_user(db_session, UserRole.student)
    project = make_project(db_session, owner)

    resp = client.post(f"/api/projects/{project.id}/progress", data={"content": "x"}, headers=auth_headers(other_student))
    assert resp.status_code == 403


def test_guide_cannot_post_progress(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide)

    resp = client.post(f"/api/projects/{project.id}/progress", data={"content": "x"}, headers=auth_headers(guide))
    assert resp.status_code == 403


def test_progress_updates_are_newest_first_and_cumulative(client, db_session):
    student = make_user(db_session, UserRole.student)
    project = make_project(db_session, student)

    client.post(f"/api/projects/{project.id}/progress", data={"content": "first update"}, headers=auth_headers(student))
    client.post(f"/api/projects/{project.id}/progress", data={"content": "second update"}, headers=auth_headers(student))

    resp = client.get(f"/api/projects/{project.id}/progress", headers=auth_headers(student))
    assert resp.status_code == 200
    bodies = [p["content"] for p in resp.json()]
    assert bodies == ["second update", "first update"]  # newest first, nothing lost


# ── Guide feedback: informal marks, separate from the official reviewer track ───

def test_guide_can_set_feedback(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide)

    resp = client.put(f"/api/projects/{project.id}/guide-feedback",
                       json={"overallScore": 65.0, "comment": "Good start, needs more depth."},
                       headers=auth_headers(guide))
    assert resp.status_code == 200
    assert resp.json()["overallScore"] == 65.0

    # Student can read it immediately (no publish gate — informal feedback).
    resp = client.get(f"/api/projects/{project.id}/guide-feedback", headers=auth_headers(student))
    assert resp.status_code == 200
    assert resp.json()["overallScore"] == 65.0


def test_reviewer_cannot_set_guide_feedback(client, db_session):
    student = make_user(db_session, UserRole.student)
    reviewer = make_user(db_session, UserRole.reviewer)
    project = make_project(db_session, student, reviewer=reviewer)

    resp = client.put(f"/api/projects/{project.id}/guide-feedback",
                       json={"overallScore": 90.0, "comment": "x"},
                       headers=auth_headers(reviewer))
    assert resp.status_code == 403


def test_unassigned_guide_cannot_set_feedback(client, db_session):
    student = make_user(db_session, UserRole.student)
    assigned_guide = make_user(db_session, UserRole.guide)
    outsider_guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=assigned_guide)

    resp = client.put(f"/api/projects/{project.id}/guide-feedback",
                       json={"overallScore": 50.0, "comment": "x"},
                       headers=auth_headers(outsider_guide))
    assert resp.status_code == 403
