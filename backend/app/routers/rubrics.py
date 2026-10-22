from fastapi import APIRouter, HTTPException, status

from app.dependencies import DB, CurrentUser, CurrentCoordinator, CurrentHOD
from app.models.rubric import Rubric
from app.schemas.rubric import RubricCreate, RubricOut
from app.utils.audit import log_audit

router = APIRouter(tags=["Rubrics"])


def _to_out(rubric: Rubric) -> RubricOut:
    from app.schemas.rubric import RubricCriteriaItem
    return RubricOut(
        rubricId=str(rubric.id),
        name=rubric.name,
        department=rubric.department,
        academicYear=rubric.academic_year,
        version=rubric.version,
        supersedesId=str(rubric.supersedes_id) if rubric.supersedes_id else None,
        createdBy=rubric.creator.name,
        isApproved=rubric.is_approved,
        criteria=[RubricCriteriaItem(**c) for c in (rubric.criteria or [])],
        createdAt=rubric.created_at.isoformat(),
    )


@router.get("/rubrics", response_model=list[RubricOut])
def list_rubrics(current_user: CurrentUser, db: DB):
    rubrics = db.query(Rubric).order_by(Rubric.created_at.desc()).all()
    return [_to_out(r) for r in rubrics]


@router.post("/rubrics", response_model=RubricOut, status_code=status.HTTP_201_CREATED)
def create_rubric(payload: RubricCreate, current_user: CurrentCoordinator, db: DB):
    """Coordinator-only — guides no longer touch official rubrics (see
    guide_feedback.py for their informal-feedback channel instead)."""
    rubric = Rubric(
        name=payload.name,
        department=payload.department,
        academic_year=payload.academicYear,
        created_by_id=current_user.id,
        is_approved=False,
        version=1,
        criteria=[c.model_dump() for c in payload.criteria],
    )
    db.add(rubric)
    db.commit()
    db.refresh(rubric)
    return _to_out(rubric)


@router.put("/rubrics/{rubric_id}", response_model=RubricOut, status_code=status.HTTP_201_CREATED)
def edit_rubric(rubric_id: str, payload: RubricCreate, current_user: CurrentCoordinator, db: DB):
    """Edit a rubric. If it was already approved, this creates a NEW rubric
    row (version + 1, unapproved) instead of mutating it in place, so a
    rubric that may already have been used to score something can't
    silently change out from under those scores. An unapproved draft is
    edited in place."""
    existing = db.query(Rubric).filter(Rubric.id == rubric_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Rubric not found")

    if not existing.is_approved:
        existing.name = payload.name
        existing.department = payload.department
        existing.academic_year = payload.academicYear
        existing.criteria = [c.model_dump() for c in payload.criteria]
        db.commit()
        db.refresh(existing)
        return _to_out(existing)

    new_rubric = Rubric(
        name=payload.name,
        department=payload.department,
        academic_year=payload.academicYear,
        created_by_id=current_user.id,
        is_approved=False,
        version=existing.version + 1,
        supersedes_id=existing.id,
        criteria=[c.model_dump() for c in payload.criteria],
    )
    db.add(new_rubric)
    db.commit()
    db.refresh(new_rubric)
    return _to_out(new_rubric)


@router.patch("/rubrics/{rubric_id}/approve", response_model=RubricOut)
def approve_rubric(rubric_id: str, current_user: CurrentHOD, db: DB):
    rubric = db.query(Rubric).filter(Rubric.id == rubric_id).first()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    rubric.is_approved = True
    log_audit(db, current_user, "approve_rubric", "rubric", str(rubric.id), {
        "name": rubric.name, "department": rubric.department, "version": rubric.version,
    })
    db.commit()
    db.refresh(rubric)
    return _to_out(rubric)
