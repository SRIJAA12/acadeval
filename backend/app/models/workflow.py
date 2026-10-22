"""RBAC workflow support: audit log, milestones, project discussion, and
in-app notifications. Kept in one module since they're all thin, closely
related additions to the academic-administration workflow (Person 2/3 scope)
rather than part of the scoring/graph engine.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Integer, Enum, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AuditLog(Base):
    """General who-changed-what trail. Separate from ScoreOverrideHistory
    (which is score-specific and already existed) — this covers role
    changes, assignment changes, rubric approval, and publish actions."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    actor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class MilestoneStatus(str, enum.Enum):
    pending = "pending"
    submitted = "submitted"
    approved = "approved"
    revision_requested = "revision_requested"


class Milestone(Base):
    """Standard academic-progress checklist per project. Seeded automatically
    when a project is created; the student submits notes per milestone and
    the assigned guide approves or requests revision."""
    __tablename__ = "milestones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[MilestoneStatus] = mapped_column(
        Enum(MilestoneStatus), nullable=False, default=MilestoneStatus.pending
    )
    student_submission: Mapped[str | None] = mapped_column(Text, nullable=True)
    guide_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship("Project", back_populates="milestones")


STANDARD_MILESTONES = [
    ("Problem Identification", "Define the problem statement and project scope."),
    ("Literature Review", "Summarize related work and how this project differs."),
    ("Design", "System architecture, data flow, and technology choices."),
    ("Implementation", "Core implementation progress and key modules completed."),
    ("Testing & Documentation", "Test results, evaluation, and final report/documentation."),
]


class DiscussionMessage(Base):
    """A project-scoped thread between the student and their assigned
    guide/reviewer. Private to the project's participants + HOD."""
    __tablename__ = "discussion_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    author_name: Mapped[str] = mapped_column(String(200), nullable=False)
    author_role: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_by: Mapped[list] = mapped_column(JSONB, default=list)  # list of user_id strings
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    project: Mapped["Project"] = relationship("Project", back_populates="discussion_messages")


class ProgressUpdate(Base):
    """Append-only progress log the student posts to as work happens. Never
    edited or deleted — each entry is a point-in-time snapshot; the newest
    is what guide/reviewer/HOD see first. This is deliberately separate from
    the structured Milestone checklist: it's the free-form "here's where I
    am" post the student controls the cadence of."""
    __tablename__ = "progress_updates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    author_name: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Optional attachment (doc/ppt) and/or an updated repo link — both optional,
    # on top of the required text note.
    attachment_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    attachment_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    project: Mapped["Project"] = relationship("Project", back_populates="progress_updates")


class GuideFeedback(Base):
    """The guide's own informal mark + comments for a project — explicitly
    NOT the official grade (that's the reviewer's EvaluationReport track).
    One row per project; the guide updates it as the student's progress
    updates come in, so it always reflects their latest read."""
    __tablename__ = "guide_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), unique=True, nullable=False
    )
    guide_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    guide_name: Mapped[str] = mapped_column(String(200), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    comment: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    project: Mapped["Project"] = relationship("Project", back_populates="guide_feedback")


class Notification(Base):
    """In-app notification feed, separate from the existing email side-channel
    in notification_service.py."""
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, default="")
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
