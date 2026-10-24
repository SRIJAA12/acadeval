"""Score Coach endpoints: why a project got its AI score, how to improve it,
what 100% requires, and an Ask box. Read access follows ensure_participant
(the project's student, its assigned guide once the student has submitted to
them, its reviewer, or HOD). Only the project's own student can ask questions."""
import time
from collections import defaultdict, deque
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies import DB, CurrentUser
from app.models.evaluation import EvaluationReport
from app.models.project import Project
from app.models.user import UserRole
from app.services import score_coach
from app.utils.authz import ensure_participant

router = APIRouter(tags=["Score Coach"])

ASK_LIMIT = 10
ASK_WINDOW_SECONDS = 60
_ask_log: dict[str, deque] = defaultdict(deque)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=score_coach.MAX_QUESTION_CHARS)
    dimensionKey: Optional[str] = Field(default=None, max_length=40)


def _load(project_id: str, db) -> tuple[Project, Optional[EvaluationReport]]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    report = db.query(EvaluationReport).filter(EvaluationReport.project_id == project.id).first()
    return project, report


@router.get("/projects/{project_id}/score-coach")
def get_score_coach(project_id: str, current_user: CurrentUser, db: DB):
    project, report = _load(project_id, db)
    ensure_participant(project, current_user)
    return score_coach.build_coaching(project, report)


@router.post("/projects/{project_id}/score-coach/ask")
def ask_score_coach(project_id: str, body: AskRequest, current_user: CurrentUser, db: DB):
    project, report = _load(project_id, db)
    if current_user.role != UserRole.student or project.student_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the project's student can ask the Score Coach.")

    now = time.monotonic()
    window = _ask_log[str(current_user.id)]
    while window and now - window[0] > ASK_WINDOW_SECONDS:
        window.popleft()
    if len(window) >= ASK_LIMIT:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many questions. Please wait a minute and try again.")
    window.append(now)

    if body.dimensionKey and body.dimensionKey not in score_coach.NAMES:
        raise HTTPException(status_code=422, detail="Unknown dimension")
    coaching = score_coach.build_coaching(project, report)
    return score_coach.answer_question(coaching, body.question, body.dimensionKey)
