"""Team allocation (coordinator-created, from the roster's Team ID column),
team discussion, and task/to-do tracking (personal or team-scoped). See
app/routers/teams.py and app/routers/coordinator.py (upload_roster)."""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Enum, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TeamRole(str, enum.Enum):
    member = "member"
    lead = "lead"


class Team(Base):
    """A real student team, keyed by team_code — the same string the
    coordinator's Excel roster and review-round assignment already use as
    Project.team_id, so bulk reviewer assignment-by-team keeps working
    unchanged."""
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    memberships: Mapped[list["TeamMembership"]] = relationship(
        "TeamMembership", back_populates="team", cascade="all, delete-orphan"
    )


class TeamMembership(Base):
    __tablename__ = "team_memberships"
    __table_args__ = (UniqueConstraint("team_id", "student_id", name="uq_team_memberships_team_student"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False, index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[TeamRole] = mapped_column(Enum(TeamRole), nullable=False, default=TeamRole.member)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    team: Mapped["Team"] = relationship("Team", back_populates="memberships")


class TeamMessage(Base):
    """Team-scoped discussion thread — same shape as DiscussionMessage but
    open to every member, not just a guide<->student pair."""
    __tablename__ = "team_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=False, index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    author_name: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mentioned_user_ids: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class TaskStatus(str, enum.Enum):
    pending = "pending"
    done = "done"


class TaskSource(str, enum.Enum):
    manual = "manual"
    guide_request = "guide_request"
    review_scheduled = "review_scheduled"
    team = "team"


class Task(Base):
    """A to-do item. project_id-only = personal (student's own to-do for
    that project); team_id set = a team task any member assigned to any
    other member. Auto-created for guide requests and scheduled review
    rounds — see app/routers/teams.py and app/routers/coordinator.py."""
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, index=True)
    assignee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), nullable=False, default=TaskStatus.pending)
    source: Mapped[TaskSource] = mapped_column(Enum(TaskSource), nullable=False, default=TaskSource.manual)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
