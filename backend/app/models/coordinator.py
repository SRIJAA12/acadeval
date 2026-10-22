"""Coordinator-owned workflow: bulk guide/student allocation via Excel roster
upload, reviewer slot scheduling per review round, and the resulting
per-round scores. Kept separate from workflow.py since this is a distinct
ownership area (coordinator, not guide/student)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RosterAllocation(Base):
    """One row per roster entry from the coordinator's Excel upload. Applied
    immediately to any already-submitted project matching the roll number;
    otherwise stays pending and is applied automatically the moment that
    student submits (see app/routers/projects.py upload_project)."""
    __tablename__ = "roster_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    roll_no: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    student_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    team_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    guide_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    guide_email_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)  # kept even if guide_id lookup failed
    domain: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    applied_project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)  # e.g. "guide email not found"
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class ReviewRound(Base):
    """A scheduled review event (e.g. 'Review 1', 'Final Review'). Each round
    produces its own independent scores (RoundEvaluation) — a project can
    have several rounds before, optionally, one marked final."""
    __tablename__ = "review_rounds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    assignments: Mapped[list["ReviewSlotAssignment"]] = relationship(
        "ReviewSlotAssignment", back_populates="round", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["RoundEvaluation"]] = relationship(
        "RoundEvaluation", back_populates="round", cascade="all, delete-orphan"
    )


class ReviewSlotAssignment(Base):
    """Coordinator's schedule entry: 'Reviewer 2' evaluates this project in
    this round, at this time; credentials for the slot were emailed to
    staff_email for this round specifically."""
    __tablename__ = "review_slot_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review_rounds.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    reviewer_slot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    staff_email: Mapped[str] = mapped_column(String(255), nullable=False)  # real person this round's credentials went to
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    credential_email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    round: Mapped["ReviewRound"] = relationship("ReviewRound", back_populates="assignments")
    project: Mapped["Project"] = relationship("Project", back_populates="review_slot_assignments")


class RoundEvaluation(Base):
    """The reviewer's score for one project in one round — independent of
    every other round's score. When the round is_final, publishing this also
    syncs the project's official EvaluationReport (see app/routers/reviews.py)."""
    __tablename__ = "round_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("review_rounds.id"), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    reviewer_slot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    novelty_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feasibility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    technical_depth_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    clarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    similarity_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    publication_potential_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment: Mapped[str] = mapped_column(Text, default="")

    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    round: Mapped["ReviewRound"] = relationship("ReviewRound", back_populates="evaluations")
    project: Mapped["Project"] = relationship("Project", back_populates="round_evaluations")
