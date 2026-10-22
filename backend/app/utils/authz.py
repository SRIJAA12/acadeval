"""Assignment-scoped authorization. Role-only checks (require_role in
app/dependencies.py) answer "is this person a guide/reviewer/HOD?" — these
helpers answer the question that was previously unchecked anywhere in the
codebase: "is this specific guide/reviewer actually assigned to THIS
project?" HOD always passes; an unassigned project is visible to any
guide/reviewer so it can still be triaged, but actions that change state
(score, publish, notes) require assignment once one exists.
"""
from fastapi import HTTPException, status

from app.models.project import Project
from app.models.user import User, UserRole


def is_assigned(project: Project, user: User) -> bool:
    if user.role == UserRole.hod:
        return True
    if user.role == UserRole.guide:
        # The guide sees nothing about a project — not even that it exists —
        # until the student explicitly clicks "Submit to Guide" (requires
        # score > 30). Being the roster-assigned guide alone is not enough.
        return project.assigned_guide_id == user.id and project.guide_submitted_at is not None
    if user.role == UserRole.reviewer:
        return project.assigned_reviewer_id == user.id
    return False


def ensure_assigned(project: Project, user: User) -> None:
    """Raise 403 unless the user is HOD, or is the specific guide/reviewer
    assigned to this project. An unassigned project is visible to nobody but
    HOD until HOD assigns it — this is the deliberate, strict reading: a
    guide/reviewer should never be able to act on (or discover) a project
    just by guessing its id."""
    if not is_assigned(project, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this project.",
        )


def ensure_participant(project: Project, user: User) -> None:
    """Raise 403 unless the user is the project's own student, its assigned
    guide/reviewer, or HOD. Used for shared spaces (milestones, discussion)
    where the student also needs access, not just faculty."""
    if user.role == UserRole.student:
        if project.student_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return
    ensure_assigned(project, user)


def ensure_guide_student_participant(project: Project, user: User) -> None:
    """Raise 403 unless the user is the project's own student, its assigned
    guide, or HOD. Deliberately excludes the reviewer — the discussion forum
    is a guide<->student space; the reviewer's channel is the official score
    + internal notes, not this thread."""
    if user.role == UserRole.student:
        if project.student_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return
    if user.role == UserRole.hod:
        return
    if user.role == UserRole.guide and project.assigned_guide_id == user.id and project.guide_submitted_at is not None:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="The discussion forum is between the student and their assigned guide only.",
    )


def visible_projects_query(query, user: User):
    """Apply assignment scoping to a Project query for list endpoints.
    HOD: unrestricted. Guide/Reviewer: only projects assigned to them."""
    if user.role == UserRole.guide:
        return query.filter(Project.assigned_guide_id == user.id, Project.guide_submitted_at.isnot(None))
    if user.role == UserRole.reviewer:
        return query.filter(Project.assigned_reviewer_id == user.id)
    return query
