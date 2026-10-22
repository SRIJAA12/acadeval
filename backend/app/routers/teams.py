"""Team allocation, team discussion, and task/to-do tracking. Teams are
created by the Coordinator (via the roster's Team ID column — see
upload_roster in app/routers/coordinator.py); every endpoint here is
member-only except the read-only coordinator/HOD oversight list."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.dependencies import DB, CurrentUser, CurrentStudent, CurrentCoordinatorOrHOD
from app.models.team import Team, TeamMembership, TeamMessage, Task, TaskStatus
from app.models.project import Project
from app.models.user import User, UserRole
from app.schemas.team import (
    TeamOut, TeamMemberOut, TeamMessageCreate, TeamMessageOut,
    TaskCreate, TaskUpdateRequest, TaskOut,
)
from app.utils.notify import notify

router = APIRouter(tags=["Teams"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _team_members(db, team_id) -> list[TeamMemberOut]:
    rows = (
        db.query(TeamMembership, User)
        .join(User, User.id == TeamMembership.student_id)
        .filter(TeamMembership.team_id == team_id)
        .order_by(User.name)
        .all()
    )
    return [
        TeamMemberOut(studentId=str(u.id), name=u.name, rollNo=u.roll_no, role=m.role.value)
        for m, u in rows
    ]


def _team_to_out(db, team: Team) -> TeamOut:
    return TeamOut(
        teamId=str(team.id), teamCode=team.team_code, name=team.name,
        members=_team_members(db, team.id), createdAt=team.created_at.isoformat(),
    )


def _require_member(db, team_id: str, user: User) -> Team:
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    if user.role in (UserRole.hod, UserRole.coordinator):
        return team
    is_member = db.query(TeamMembership).filter(
        TeamMembership.team_id == team_id, TeamMembership.student_id == user.id
    ).first()
    if not is_member:
        raise HTTPException(status_code=403, detail="You are not a member of this team")
    return team


def _task_to_out(db, task: Task) -> TaskOut:
    project = db.query(Project).filter(Project.id == task.project_id).first() if task.project_id else None
    team = db.query(Team).filter(Team.id == task.team_id).first() if task.team_id else None
    assignee = db.query(User).filter(User.id == task.assignee_id).first()
    creator = db.query(User).filter(User.id == task.created_by_id).first() if task.created_by_id else None
    return TaskOut(
        taskId=str(task.id), projectId=str(task.project_id) if task.project_id else None,
        projectTitle=project.title if project else None,
        teamId=str(task.team_id) if task.team_id else None,
        teamCode=team.team_code if team else None,
        assigneeId=str(task.assignee_id), assigneeName=assignee.name if assignee else "",
        createdByName=creator.name if creator else None,
        title=task.title, description=task.description, status=task.status.value, source=task.source.value,
        dueDate=task.due_date.isoformat() if task.due_date else None,
        createdAt=task.created_at.isoformat(),
        completedAt=task.completed_at.isoformat() if task.completed_at else None,
    )


# ── Teams ─────────────────────────────────────────────────────────────────────

@router.get("/teams/my", response_model=list[TeamOut])
def list_my_teams(current_user: CurrentStudent, db: DB):
    team_ids = [m.team_id for m in db.query(TeamMembership).filter(TeamMembership.student_id == current_user.id).all()]
    teams = db.query(Team).filter(Team.id.in_(team_ids)).order_by(Team.created_at.desc()).all()
    return [_team_to_out(db, t) for t in teams]


@router.get("/teams/{team_id}", response_model=TeamOut)
def get_team(team_id: str, current_user: CurrentUser, db: DB):
    team = _require_member(db, team_id, current_user)
    return _team_to_out(db, team)


# ── Team discussion ──────────────────────────────────────────────────────────

@router.get("/teams/{team_id}/messages", response_model=list[TeamMessageOut])
def list_team_messages(team_id: str, current_user: CurrentUser, db: DB):
    _require_member(db, team_id, current_user)
    msgs = db.query(TeamMessage).filter(TeamMessage.team_id == team_id).order_by(TeamMessage.created_at).all()
    return [
        TeamMessageOut(
            messageId=str(m.id), authorId=str(m.author_id), authorName=m.author_name, body=m.body,
            mentionedUserIds=m.mentioned_user_ids or [], createdAt=m.created_at.isoformat(),
        )
        for m in msgs
    ]


@router.post("/teams/{team_id}/messages", response_model=TeamMessageOut, status_code=status.HTTP_201_CREATED)
def post_team_message(team_id: str, payload: TeamMessageCreate, current_user: CurrentUser, db: DB):
    team = _require_member(db, team_id, current_user)
    members = _team_members(db, team.id)

    # Simple @mention: substring-match "@Full Name" against every other member.
    mentioned_ids: list[str] = []
    for member in members:
        if member.studentId == str(current_user.id):
            continue
        if f"@{member.name}".lower() in payload.body.lower():
            mentioned_ids.append(member.studentId)

    msg = TeamMessage(
        team_id=team.id, author_id=current_user.id, author_name=current_user.name,
        body=payload.body, mentioned_user_ids=mentioned_ids,
    )
    db.add(msg)

    for member_id in mentioned_ids:
        notify(db, member_id, "team_mention", f"{current_user.name} mentioned you in {team.name or team.team_code}",
               body=payload.body[:140], link=f"/student/team-progress/{team.id}")
    # Also let everyone else in the team know about new activity, mentioned or not.
    for member in members:
        if member.studentId != str(current_user.id) and member.studentId not in mentioned_ids:
            notify(db, member.studentId, "team_message", f"New message in {team.name or team.team_code}",
                   body=payload.body[:140], link=f"/student/team-progress/{team.id}")

    db.commit()
    db.refresh(msg)
    return TeamMessageOut(
        messageId=str(msg.id), authorId=str(msg.author_id), authorName=msg.author_name, body=msg.body,
        mentionedUserIds=msg.mentioned_user_ids or [], createdAt=msg.created_at.isoformat(),
    )


# ── Tasks (team-scoped and personal) ─────────────────────────────────────────

@router.get("/teams/{team_id}/tasks", response_model=list[TaskOut])
def list_team_tasks(team_id: str, current_user: CurrentUser, db: DB):
    _require_member(db, team_id, current_user)
    tasks = db.query(Task).filter(Task.team_id == team_id).order_by(Task.created_at.desc()).all()
    return [_task_to_out(db, t) for t in tasks]


@router.post("/teams/{team_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_team_task(team_id: str, payload: TaskCreate, current_user: CurrentUser, db: DB):
    team = _require_member(db, team_id, current_user)
    assignee_id = payload.assigneeId or str(current_user.id)
    if not db.query(TeamMembership).filter(TeamMembership.team_id == team.id, TeamMembership.student_id == assignee_id).first():
        raise HTTPException(status_code=422, detail="assigneeId must be a member of this team")

    due = None
    if payload.dueDate:
        try:
            due = datetime.fromisoformat(payload.dueDate)
        except ValueError:
            raise HTTPException(status_code=422, detail="dueDate must be an ISO date/datetime")

    task = Task(
        team_id=team.id, assignee_id=assignee_id, created_by_id=current_user.id,
        title=payload.title, description=payload.description, due_date=due, source="team",
    )
    db.add(task)
    if assignee_id != str(current_user.id):
        notify(db, assignee_id, "task_assigned", f"{current_user.name} assigned you a task in {team.name or team.team_code}",
               body=payload.title, link=f"/student/team-progress/{team.id}")
    db.commit()
    db.refresh(task)
    return _task_to_out(db, task)


@router.get("/tasks/my", response_model=list[TaskOut])
def list_my_tasks(current_user: CurrentStudent, db: DB):
    tasks = db.query(Task).filter(Task.assignee_id == current_user.id).order_by(Task.created_at.desc()).all()
    return [_task_to_out(db, t) for t in tasks]


@router.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_personal_task(payload: TaskCreate, current_user: CurrentUser, db: DB):
    """Manual add, for the student's own per-project to-do, or a guide
    assigning a task to their (submitted-to) student."""
    project = None
    if payload.projectId:
        project = db.query(Project).filter(Project.id == payload.projectId).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role == UserRole.student:
        # A project is optional — this can be a general personal reminder,
        # or tied to one of the student's own projects.
        if project and project.student_id != current_user.id:
            raise HTTPException(status_code=422, detail="Students can only add to-dos on their own projects")
        assignee_id = str(current_user.id)
        source = "manual"
    elif current_user.role == UserRole.guide:
        if not project or project.assigned_guide_id != current_user.id or project.guide_submitted_at is None:
            raise HTTPException(status_code=403, detail="Only the assigned guide of a submitted project can assign a task")
        assignee_id = str(project.student_id)
        source = "guide_request"
    else:
        raise HTTPException(status_code=403, detail="Only students (for themselves) or guides (for their students) can create tasks here")

    due = None
    if payload.dueDate:
        try:
            due = datetime.fromisoformat(payload.dueDate)
        except ValueError:
            raise HTTPException(status_code=422, detail="dueDate must be an ISO date/datetime")

    task = Task(
        project_id=project.id if project else None, assignee_id=assignee_id, created_by_id=current_user.id,
        title=payload.title, description=payload.description, due_date=due, source=source,
    )
    db.add(task)
    if source == "guide_request":
        notify(db, assignee_id, "task_assigned", f"Your guide assigned you a task on \"{project.title}\"",
               body=payload.title, link=f"/student/todo")
    db.commit()
    db.refresh(task)
    return _task_to_out(db, task)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: str, payload: TaskUpdateRequest, current_user: CurrentUser, db: DB):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    allowed = (
        current_user.role == UserRole.hod
        or task.assignee_id == current_user.id
        or task.created_by_id == current_user.id
    )
    if not allowed:
        raise HTTPException(status_code=403, detail="Only the assignee, creator, or HOD can update this task")

    if payload.status not in (TaskStatus.pending.value, TaskStatus.done.value):
        raise HTTPException(status_code=422, detail="status must be 'pending' or 'done'")
    task.status = TaskStatus(payload.status)
    task.completed_at = datetime.now(timezone.utc) if task.status == TaskStatus.done else None
    db.commit()
    db.refresh(task)
    return _task_to_out(db, task)


# ── Coordinator / HOD oversight ──────────────────────────────────────────────

@router.get("/coordinator/teams", response_model=list[TeamOut])
def list_all_teams(current_user: CurrentCoordinatorOrHOD, db: DB):
    teams = db.query(Team).order_by(Team.created_at.desc()).all()
    return [_team_to_out(db, t) for t in teams]
