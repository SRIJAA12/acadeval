"""API-level tests for teams, team discussion/tasks, and the student to-do
list (Team/TeamMembership/TeamMessage/Task — see app/routers/teams.py)."""
import uuid

from app.models.team import Team, TeamMembership
from app.models.user import UserRole
from tests.conftest import make_user, auth_headers
from tests.test_rbac import make_project


def make_team(db_session, *students, code: str | None = None) -> Team:
    team = Team(id=uuid.uuid4(), team_code=code or f"TEAM-{uuid.uuid4().hex[:6]}")
    db_session.add(team)
    db_session.flush()
    for s in students:
        db_session.add(TeamMembership(team_id=team.id, student_id=s.id))
    db_session.commit()
    db_session.refresh(team)
    return team


# ── Team membership & access ─────────────────────────────────────────────────

def test_member_sees_team_in_my_teams(client, db_session):
    alice = make_user(db_session, UserRole.student, "Alice")
    bob = make_user(db_session, UserRole.student, "Bob")
    team = make_team(db_session, alice, bob)

    resp = client.get("/api/teams/my", headers=auth_headers(alice))
    assert resp.status_code == 200
    ids = {t["teamId"] for t in resp.json()}
    assert str(team.id) in ids
    members = resp.json()[0]["members"]
    assert {m["name"] for m in members} == {"Alice", "Bob"}


def test_non_member_cannot_access_team(client, db_session):
    alice = make_user(db_session, UserRole.student, "Alice")
    outsider = make_user(db_session, UserRole.student, "Outsider")
    team = make_team(db_session, alice)

    resp = client.get(f"/api/teams/{team.id}", headers=auth_headers(outsider))
    assert resp.status_code == 403


# ── Team discussion + @mention ───────────────────────────────────────────────

def test_member_can_post_and_mention(client, db_session):
    alice = make_user(db_session, UserRole.student, "Alice")
    bob = make_user(db_session, UserRole.student, "Bob")
    team = make_team(db_session, alice, bob)

    resp = client.post(f"/api/teams/{team.id}/messages", json={"body": "@Bob can you review this?"},
                        headers=auth_headers(alice))
    assert resp.status_code == 201
    assert resp.json()["mentionedUserIds"] == [str(bob.id)]

    resp = client.get(f"/api/notifications", headers=auth_headers(bob))
    assert resp.status_code == 200
    assert any(n["type"] == "team_mention" for n in resp.json())


def test_non_member_cannot_post_to_team(client, db_session):
    alice = make_user(db_session, UserRole.student, "Alice")
    outsider = make_user(db_session, UserRole.student, "Outsider")
    team = make_team(db_session, alice)

    resp = client.post(f"/api/teams/{team.id}/messages", json={"body": "hi"}, headers=auth_headers(outsider))
    assert resp.status_code == 403


# ── Team tasks: any member can assign to any other member ──────────────────────

def test_member_can_assign_task_to_another_member(client, db_session):
    alice = make_user(db_session, UserRole.student, "Alice")
    bob = make_user(db_session, UserRole.student, "Bob")
    team = make_team(db_session, alice, bob)

    resp = client.post(f"/api/teams/{team.id}/tasks", json={"title": "Write tests", "assigneeId": str(bob.id)},
                        headers=auth_headers(alice))
    assert resp.status_code == 201
    assert resp.json()["assigneeId"] == str(bob.id)
    assert resp.json()["source"] == "team"

    resp = client.get("/api/tasks/my", headers=auth_headers(bob))
    assert resp.status_code == 200
    assert any(t["title"] == "Write tests" for t in resp.json())


def test_cannot_assign_team_task_to_non_member(client, db_session):
    alice = make_user(db_session, UserRole.student, "Alice")
    outsider = make_user(db_session, UserRole.student, "Outsider")
    team = make_team(db_session, alice)

    resp = client.post(f"/api/teams/{team.id}/tasks", json={"title": "x", "assigneeId": str(outsider.id)},
                        headers=auth_headers(alice))
    assert resp.status_code == 422


# ── Personal / guide-assigned tasks ──────────────────────────────────────────

def test_student_can_create_task_without_a_project(client, db_session):
    student = make_user(db_session, UserRole.student)

    resp = client.post("/api/tasks", json={"title": "Buy a notebook"}, headers=auth_headers(student))
    assert resp.status_code == 201
    assert resp.json()["projectId"] is None
    assert resp.json()["source"] == "manual"


def test_guide_can_assign_task_on_submitted_project(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide)  # guide_submitted=True by default

    resp = client.post("/api/tasks", json={"title": "Add related work", "projectId": str(project.id)},
                        headers=auth_headers(guide))
    assert resp.status_code == 201
    assert resp.json()["assigneeId"] == str(student.id)
    assert resp.json()["source"] == "guide_request"


def test_guide_cannot_assign_task_before_submission(client, db_session):
    student = make_user(db_session, UserRole.student)
    guide = make_user(db_session, UserRole.guide)
    project = make_project(db_session, student, guide=guide, guide_submitted=False)

    resp = client.post("/api/tasks", json={"title": "x", "projectId": str(project.id)}, headers=auth_headers(guide))
    assert resp.status_code == 403


def test_only_assignee_creator_or_hod_can_toggle_task(client, db_session):
    student = make_user(db_session, UserRole.student)
    outsider = make_user(db_session, UserRole.student)

    resp = client.post("/api/tasks", json={"title": "x"}, headers=auth_headers(student))
    task_id = resp.json()["taskId"]

    resp = client.patch(f"/api/tasks/{task_id}", json={"status": "done"}, headers=auth_headers(outsider))
    assert resp.status_code == 403

    resp = client.patch(f"/api/tasks/{task_id}", json={"status": "done"}, headers=auth_headers(student))
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
    assert resp.json()["completedAt"] is not None
