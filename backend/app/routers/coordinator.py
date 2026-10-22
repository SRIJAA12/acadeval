"""Coordinator router: bulk guide/team allocation via Excel roster upload,
reviewer slot account management, scheduled review rounds, and per-round
reviewer scoring. See the class docstrings in app/models/coordinator.py for
the data model this implements."""
import logging
import secrets
import string
import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile, File, status

from app.dependencies import DB, CurrentCoordinator, CurrentCoordinatorOrHOD, CurrentUser
from app.models.project import Project
from app.models.user import User, UserRole
from app.models.coordinator import RosterAllocation, ReviewRound, ReviewSlotAssignment, RoundEvaluation
from app.models.rubric import Rubric
from app.models.team import Team, TeamMembership, Task, TaskSource
from app.schemas.coordinator import (
    RosterRowResult, RosterUploadResponse, RosterAllocationOut,
    ReviewerSlotCreate, ReviewerSlotOut,
    ReviewRoundCreate, ReviewRoundOut,
    ReviewSlotAssignmentCreate, ReviewSlotAssignmentOut,
    RoundEvaluationUpdateRequest, RoundEvaluationOut,
    CoordinatorOverview,
)
from app.utils.auth import hash_password
from app.utils.audit import log_audit
from app.utils.notify import notify

log = logging.getLogger(__name__)

router = APIRouter(prefix="/coordinator", tags=["Coordinator"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    safe = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    while "--" in safe:
        safe = safe.replace("--", "-")
    return safe or "slot"


def _gen_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _normalize_header(h) -> str:
    return str(h or "").strip().lower().replace(" ", "_").replace("-", "_")


def _get_project_or_404(project_id: str, db) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ── Overview ──────────────────────────────────────────────────────────────────

@router.get("/overview", response_model=CoordinatorOverview)
def get_overview(current_user: CurrentCoordinatorOrHOD, db: DB):
    total_projects = db.query(Project).count()
    unallocated = db.query(Project).filter(Project.assigned_guide_id.is_(None)).count()
    pending_roster = db.query(RosterAllocation).filter(RosterAllocation.is_applied.is_(False)).count()
    reviewer_slots = db.query(User).filter(User.is_reviewer_slot.is_(True)).count()
    active_rounds = db.query(ReviewRound).count()
    rubrics_pending = db.query(Rubric).filter(Rubric.is_approved.is_(False)).count()
    return CoordinatorOverview(
        totalProjects=total_projects,
        unallocatedProjects=unallocated,
        pendingRosterRows=pending_roster,
        reviewerSlotCount=reviewer_slots,
        activeRoundCount=active_rounds,
        rubricsPendingApproval=rubrics_pending,
    )


# ── Roster allocation (guide/team assignment via Excel) ────────────────────────

@router.post("/roster/upload", response_model=RosterUploadResponse)
def upload_roster(current_user: CurrentCoordinator, db: DB, file: UploadFile = File(...)):
    """Expected columns (header row, any order, case-insensitive):
    Roll No | Student Email (optional) | Team ID (optional) | Guide Email | Domain (optional)
    Applies immediately to any already-submitted project matching the roll
    number; otherwise the allocation stays pending and is applied the moment
    that student submits (see app/routers/projects.py)."""
    try:
        import openpyxl
    except ImportError:
        raise HTTPException(status_code=500, detail="Excel support (openpyxl) is not installed on the server.")

    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=422, detail="Upload an .xlsx file")

    raw = file.file.read()
    try:
        wb = openpyxl.load_workbook(BytesIO(raw), read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Could not read the Excel file: {exc}") from exc

    if not rows:
        raise HTTPException(status_code=422, detail="The sheet is empty")

    headers = [_normalize_header(h) for h in rows[0]]

    def _col(row: tuple, *names: str):
        for name in names:
            if name in headers:
                val = row[headers.index(name)]
                if val is not None and str(val).strip():
                    return str(val).strip()
        return None

    results: list[RosterRowResult] = []
    applied = pending = errors = 0

    for i, row in enumerate(rows[1:], start=2):
        if row is None or all(v is None for v in row):
            continue
        roll_no = _col(row, "roll_no", "rollno", "roll_number")
        if not roll_no:
            results.append(RosterRowResult(rowNumber=i, rollNo="", status="error", message="Missing Roll No"))
            errors += 1
            continue

        student_email = _col(row, "student_email", "email")
        team_id = _col(row, "team_id", "teamid", "team")
        guide_email = _col(row, "guide_email", "guideemail")
        domain = _col(row, "domain")

        guide = None
        error_msg = None
        if guide_email:
            guide = db.query(User).filter(User.email == guide_email.lower(), User.role == UserRole.guide).first()
            if not guide:
                error_msg = f"Guide email not found or not a guide: {guide_email}"
        else:
            error_msg = "Missing Guide Email"

        allocation = RosterAllocation(
            roll_no=roll_no,
            student_email=student_email.lower() if student_email else None,
            team_id=team_id,
            guide_id=guide.id if guide else None,
            guide_email_raw=guide_email,
            domain=domain,
            uploaded_by_id=current_user.id,
            error=error_msg,
        )
        db.add(allocation)
        db.flush()

        if error_msg:
            results.append(RosterRowResult(rowNumber=i, rollNo=roll_no, status="error", message=error_msg))
            errors += 1
            continue

        # Apply immediately if the student already has a submitted project.
        student = db.query(User).filter(
            (User.roll_no == roll_no) | (User.email == (student_email.lower() if student_email else "__none__"))
        ).first()

        # Team membership is independent of any project — the student should
        # see their team the moment the roster is uploaded, not only once
        # they submit. find-or-create the Team by team_code, add the member.
        if team_id and student:
            team = db.query(Team).filter(Team.team_code == team_id).first()
            if not team:
                team = Team(team_code=team_id, created_by_id=current_user.id)
                db.add(team)
                db.flush()
            if not db.query(TeamMembership).filter(
                TeamMembership.team_id == team.id, TeamMembership.student_id == student.id
            ).first():
                db.add(TeamMembership(team_id=team.id, student_id=student.id))

        existing_project = None
        if student:
            existing_project = (
                db.query(Project)
                .filter(Project.student_id == student.id)
                .order_by(Project.submitted_on.desc())
                .first()
            )
        if existing_project:
            existing_project.assigned_guide_id = guide.id
            if team_id:
                existing_project.team_id = team_id
            allocation.is_applied = True
            allocation.applied_project_id = existing_project.id
            results.append(RosterRowResult(rowNumber=i, rollNo=roll_no, status="applied",
                                            message=f"Assigned to existing project \"{existing_project.title}\""))
            applied += 1
        else:
            results.append(RosterRowResult(rowNumber=i, rollNo=roll_no, status="pending",
                                            message="Will be applied automatically when this student submits"))
            pending += 1

    log_audit(db, current_user, "upload_roster", "roster", file.filename or "roster.xlsx", {
        "rows": len(rows) - 1, "applied": applied, "pending": pending, "errors": errors,
    })
    db.commit()

    return RosterUploadResponse(totalRows=len(results), applied=applied, pending=pending, errors=errors, results=results)


@router.get("/roster", response_model=list[RosterAllocationOut])
def list_roster(current_user: CurrentCoordinatorOrHOD, db: DB, limit: int = 500):
    rows = db.query(RosterAllocation).order_by(RosterAllocation.created_at.desc()).limit(min(limit, 2000)).all()
    out = []
    for r in rows:
        guide_name = None
        if r.guide_id:
            guide = db.query(User).filter(User.id == r.guide_id).first()
            guide_name = guide.name if guide else None
        out.append(RosterAllocationOut(
            allocationId=str(r.id), rollNo=r.roll_no, studentEmail=r.student_email, teamId=r.team_id,
            guideName=guide_name, domain=r.domain, isApplied=r.is_applied, error=r.error,
            createdAt=r.created_at.isoformat(),
        ))
    return out


# ── Reviewer slot accounts ──────────────────────────────────────────────────────

@router.get("/reviewer-slots", response_model=list[ReviewerSlotOut])
def list_reviewer_slots(current_user: CurrentCoordinatorOrHOD, db: DB):
    slots = db.query(User).filter(User.is_reviewer_slot.is_(True)).order_by(User.created_at).all()
    return [
        ReviewerSlotOut(slotId=str(s.id), name=s.name, email=s.email, isActive=s.is_active, createdAt=s.created_at.isoformat())
        for s in slots
    ]


@router.post("/reviewer-slots", response_model=ReviewerSlotOut, status_code=status.HTTP_201_CREATED)
def create_reviewer_slot(payload: ReviewerSlotCreate, current_user: CurrentCoordinator, db: DB):
    base_email = f"{_slugify(payload.name)}@acadeval.edu"
    email = base_email
    suffix = 1
    while db.query(User).filter(User.email == email).first():
        suffix += 1
        email = f"{_slugify(payload.name)}{suffix}@acadeval.edu"

    slot = User(
        name=payload.name,
        email=email,
        password_hash=hash_password(_gen_password()),
        role=UserRole.reviewer,
        department="CSE",
        is_active=True,
        is_reviewer_slot=True,
    )
    db.add(slot)
    log_audit(db, current_user, "create_reviewer_slot", "user", email, {"name": payload.name})
    db.commit()
    db.refresh(slot)
    return ReviewerSlotOut(slotId=str(slot.id), name=slot.name, email=slot.email, isActive=slot.is_active, createdAt=slot.created_at.isoformat())


# ── Review rounds & scheduling ───────────────────────────────────────────────────

def _round_to_out(db, r: ReviewRound) -> ReviewRoundOut:
    assignment_count = db.query(ReviewSlotAssignment).filter(ReviewSlotAssignment.round_id == r.id).count()
    published_count = db.query(RoundEvaluation).filter(
        RoundEvaluation.round_id == r.id, RoundEvaluation.is_published.is_(True)
    ).count()
    return ReviewRoundOut(
        roundId=str(r.id), name=r.name, description=r.description,
        scheduledDate=r.scheduled_date.isoformat() if r.scheduled_date else None,
        isFinal=r.is_final, createdAt=r.created_at.isoformat(),
        assignmentCount=assignment_count, publishedCount=published_count,
    )


@router.get("/review-rounds", response_model=list[ReviewRoundOut])
def list_review_rounds(current_user: CurrentCoordinatorOrHOD, db: DB):
    rounds = db.query(ReviewRound).order_by(ReviewRound.created_at.desc()).all()
    return [_round_to_out(db, r) for r in rounds]


@router.post("/review-rounds", response_model=ReviewRoundOut, status_code=status.HTTP_201_CREATED)
def create_review_round(payload: ReviewRoundCreate, current_user: CurrentCoordinator, db: DB):
    scheduled = None
    if payload.scheduledDate:
        try:
            scheduled = datetime.fromisoformat(payload.scheduledDate)
        except ValueError:
            raise HTTPException(status_code=422, detail="scheduledDate must be an ISO date/datetime")

    round_ = ReviewRound(
        name=payload.name, description=payload.description, scheduled_date=scheduled,
        is_final=payload.isFinal, created_by_id=current_user.id,
    )
    db.add(round_)
    log_audit(db, current_user, "create_review_round", "review_round", payload.name, {"isFinal": payload.isFinal})
    db.commit()
    db.refresh(round_)
    return _round_to_out(db, round_)


@router.get("/review-rounds/{round_id}/assignments", response_model=list[ReviewSlotAssignmentOut])
def list_round_assignments(round_id: str, current_user: CurrentCoordinatorOrHOD, db: DB):
    assignments = db.query(ReviewSlotAssignment).filter(ReviewSlotAssignment.round_id == round_id).all()
    out = []
    for a in assignments:
        project = db.query(Project).filter(Project.id == a.project_id).first()
        slot = db.query(User).filter(User.id == a.reviewer_slot_id).first()
        out.append(ReviewSlotAssignmentOut(
            assignmentId=str(a.id), roundId=str(a.round_id), projectId=str(a.project_id),
            projectTitle=project.title if project else "(deleted project)",
            studentName=project.student.name if project and project.student else "",
            reviewerSlotId=str(a.reviewer_slot_id), reviewerSlotName=slot.name if slot else "(unknown)",
            staffEmail=a.staff_email, scheduledAt=a.scheduled_at.isoformat() if a.scheduled_at else None,
            credentialEmailSent=a.credential_email_sent, createdAt=a.created_at.isoformat(),
        ))
    return out


@router.post("/review-rounds/{round_id}/assignments", response_model=list[ReviewSlotAssignmentOut])
def create_round_assignment(round_id: str, payload: ReviewSlotAssignmentCreate, current_user: CurrentCoordinator, db: DB):
    """Assigns a reviewer slot to one or more projects (directly, or every
    project sharing a team_id) for this round. Regenerates the slot's
    password and emails it to staffEmail — the previous holder's password
    stops working immediately."""
    round_ = db.query(ReviewRound).filter(ReviewRound.id == round_id).first()
    if not round_:
        raise HTTPException(status_code=404, detail="Review round not found")

    slot = db.query(User).filter(User.id == payload.reviewerSlotId, User.is_reviewer_slot.is_(True)).first()
    if not slot:
        raise HTTPException(status_code=422, detail="reviewerSlotId does not refer to a reviewer slot account")

    project_ids: list[str] = []
    if payload.teamId:
        project_ids = [str(p.id) for p in db.query(Project).filter(Project.team_id == payload.teamId).all()]
        if not project_ids:
            raise HTTPException(status_code=422, detail=f"No projects found with team_id={payload.teamId}")
    elif payload.projectIds:
        project_ids = payload.projectIds
    else:
        raise HTTPException(status_code=422, detail="Provide either projectIds or teamId")

    scheduled_at = None
    if payload.scheduledAt:
        try:
            scheduled_at = datetime.fromisoformat(payload.scheduledAt)
        except ValueError:
            raise HTTPException(status_code=422, detail="scheduledAt must be an ISO date/datetime")

    # Regenerate the slot's password once for this whole assignment batch.
    new_password = _gen_password()
    slot.password_hash = hash_password(new_password)

    created: list[ReviewSlotAssignment] = []
    project_titles = []
    for pid in project_ids:
        project = _get_project_or_404(pid, db)
        project_titles.append(project.title)
        project.assigned_reviewer_id = slot.id

        assignment = ReviewSlotAssignment(
            round_id=round_.id, project_id=project.id, reviewer_slot_id=slot.id,
            staff_email=payload.staffEmail, scheduled_at=scheduled_at, created_by_id=current_user.id,
        )
        db.add(assignment)
        created.append(assignment)

        if not db.query(RoundEvaluation).filter(
            RoundEvaluation.round_id == round_.id, RoundEvaluation.project_id == project.id
        ).first():
            db.add(RoundEvaluation(round_id=round_.id, project_id=project.id, reviewer_slot_id=slot.id))

        db.add(Task(
            project_id=project.id, assignee_id=project.student_id, source=TaskSource.review_scheduled,
            due_date=scheduled_at,
            title=f"Review round \"{round_.name}\" is scheduled for your project",
        ))

    email_sent = False
    try:
        from app.services.notification_service import notify_reviewer_slot_credentials
        email_sent = notify_reviewer_slot_credentials(
            staff_email=payload.staffEmail, slot_name=slot.name, slot_login_email=slot.email,
            new_password=new_password, round_name=round_.name,
            round_date=round_.scheduled_date.isoformat() if round_.scheduled_date else None,
            project_titles=project_titles,
        )
    except Exception as exc:
        log.warning("Failed to send reviewer credential email to %s: %s", payload.staffEmail, exc)

    for a in created:
        a.credential_email_sent = email_sent

    for pid in project_ids:
        project = _get_project_or_404(pid, db)
        notify(db, project.student_id, "review_scheduled", f"\"{round_.name}\" has been scheduled for your project",
               link="/student/todo")

    log_audit(db, current_user, "assign_review_round", "review_round", str(round_.id), {
        "reviewer_slot": slot.name, "staff_email": payload.staffEmail, "project_count": len(project_ids),
        "credential_email_sent": email_sent,
    })
    db.commit()

    return list_round_assignments(round_id, current_user, db)


# ── Per-round evaluation (reviewer scores for that round) ───────────────────────

@router.get("/projects/{project_id}/round-evaluations", response_model=list[RoundEvaluationOut])
def list_round_evaluations(project_id: str, current_user: CurrentUser, db: DB):
    """Visible to the project's own student, its assigned guide/reviewer, HOD,
    and the coordinator — same broad participant rule as progress updates."""
    from app.utils.authz import ensure_participant
    project = _get_project_or_404(project_id, db)
    if current_user.role != UserRole.coordinator:
        ensure_participant(project, current_user)

    query = db.query(RoundEvaluation).filter(RoundEvaluation.project_id == project_id)
    if current_user.role == UserRole.student:
        query = query.filter(RoundEvaluation.is_published.is_(True))
    evals = query.all()
    out = []
    for e in evals:
        round_ = db.query(ReviewRound).filter(ReviewRound.id == e.round_id).first()
        slot = db.query(User).filter(User.id == e.reviewer_slot_id).first()
        out.append(RoundEvaluationOut(
            evaluationId=str(e.id), roundId=str(e.round_id), roundName=round_.name if round_ else "",
            isFinalRound=bool(round_.is_final) if round_ else False,
            projectId=str(e.project_id), reviewerSlotName=slot.name if slot else "",
            novelty=e.novelty_score, feasibility=e.feasibility_score, completeness=e.completeness_score,
            technicalDepth=e.technical_depth_score, clarity=e.clarity_score,
            similarityRisk=e.similarity_risk_score, publicationPotential=e.publication_potential_score,
            overallScore=e.overall_score, grade=e.grade, comment=e.comment,
            isPublished=e.is_published, publishedAt=e.published_at.isoformat() if e.published_at else None,
            updatedAt=e.updated_at.isoformat(),
        ))
    return out


@router.put("/projects/{project_id}/rounds/{round_id}/evaluation", response_model=RoundEvaluationOut)
def update_round_evaluation(project_id: str, round_id: str, payload: RoundEvaluationUpdateRequest, current_user: CurrentUser, db: DB):
    """The reviewer currently assigned to this project for this round. HOD
    may also edit (oversight)."""
    project = _get_project_or_404(project_id, db)
    evaluation = db.query(RoundEvaluation).filter(
        RoundEvaluation.round_id == round_id, RoundEvaluation.project_id == project_id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="No evaluation scheduled for this project in this round")

    if current_user.role == UserRole.hod:
        pass
    elif current_user.role == UserRole.reviewer and evaluation.reviewer_slot_id == current_user.id:
        pass
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the reviewer assigned to this round (or HOD) can score it")

    from app.services.assessment_engine import grade_for, overall_score

    evaluation.novelty_score = payload.novelty
    evaluation.feasibility_score = payload.feasibility
    evaluation.completeness_score = payload.completeness
    evaluation.technical_depth_score = payload.technicalDepth
    evaluation.clarity_score = payload.clarity
    evaluation.similarity_risk_score = payload.similarityRisk
    evaluation.publication_potential_score = payload.publicationPotential
    evaluation.comment = payload.comment

    computed = overall_score({
        "novelty": evaluation.novelty_score, "feasibility": evaluation.feasibility_score,
        "completeness": evaluation.completeness_score, "technical_depth": evaluation.technical_depth_score,
        "clarity": evaluation.clarity_score, "similarity_risk": evaluation.similarity_risk_score,
        "publication_potential": evaluation.publication_potential_score,
    })
    evaluation.overall_score = computed
    evaluation.grade = grade_for(computed)

    db.commit()
    db.refresh(evaluation)

    round_ = db.query(ReviewRound).filter(ReviewRound.id == round_id).first()
    slot = db.query(User).filter(User.id == evaluation.reviewer_slot_id).first()
    return RoundEvaluationOut(
        evaluationId=str(evaluation.id), roundId=str(evaluation.round_id), roundName=round_.name if round_ else "",
        isFinalRound=bool(round_.is_final) if round_ else False,
        projectId=str(evaluation.project_id), reviewerSlotName=slot.name if slot else "",
        novelty=evaluation.novelty_score, feasibility=evaluation.feasibility_score, completeness=evaluation.completeness_score,
        technicalDepth=evaluation.technical_depth_score, clarity=evaluation.clarity_score,
        similarityRisk=evaluation.similarity_risk_score, publicationPotential=evaluation.publication_potential_score,
        overallScore=evaluation.overall_score, grade=evaluation.grade, comment=evaluation.comment,
        isPublished=evaluation.is_published, publishedAt=evaluation.published_at.isoformat() if evaluation.published_at else None,
        updatedAt=evaluation.updated_at.isoformat(),
    )


@router.post("/projects/{project_id}/rounds/{round_id}/publish", status_code=status.HTTP_200_OK)
def publish_round_evaluation(project_id: str, round_id: str, current_user: CurrentUser, db: DB):
    """Publishes this round's score to the student. If the round is marked
    final, this also becomes the project's official EvaluationReport —
    exactly the same "becomes official" effect as reviews.py publish_review."""
    project = _get_project_or_404(project_id, db)
    evaluation = db.query(RoundEvaluation).filter(
        RoundEvaluation.round_id == round_id, RoundEvaluation.project_id == project_id
    ).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="No evaluation scheduled for this project in this round")

    if not (current_user.role == UserRole.hod or (current_user.role == UserRole.reviewer and evaluation.reviewer_slot_id == current_user.id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assigned reviewer (or HOD) can publish this round")

    evaluation.is_published = True
    evaluation.published_at = datetime.now(timezone.utc)

    round_ = db.query(ReviewRound).filter(ReviewRound.id == round_id).first()
    synced_official = False
    if round_ and round_.is_final and project.evaluation:
        report = project.evaluation
        report.novelty_score = evaluation.novelty_score
        report.feasibility_score = evaluation.feasibility_score
        report.completeness_score = evaluation.completeness_score
        report.technical_depth_score = evaluation.technical_depth_score
        report.clarity_score = evaluation.clarity_score
        report.similarity_risk_score = evaluation.similarity_risk_score
        report.publication_potential_score = evaluation.publication_potential_score
        report.overall_score = evaluation.overall_score or 0.0
        report.grade = evaluation.grade or report.grade
        report.published_at = datetime.now(timezone.utc)
        project.pipeline_status = project.pipeline_status.__class__.reviewed
        project.is_preliminary = False
        synced_official = True

    notify(db, project.student_id, "round_published", f"\"{round_.name if round_ else 'A review'}\" result is available for \"{project.title}\"",
           body="This is your final official grade." if synced_official else "This is a formative round result.",
           link=f"/student/report/{project.id}")

    log_audit(db, current_user, "publish_round_evaluation", "round_evaluation", str(evaluation.id), {
        "round": round_.name if round_ else None, "is_final": bool(round_ and round_.is_final), "synced_official": synced_official,
    })
    db.commit()

    return {"message": "Round evaluation published", "isFinal": bool(round_ and round_.is_final), "syncedOfficialReport": synced_official}
