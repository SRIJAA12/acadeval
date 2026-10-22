import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Enum, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    student = "student"
    guide = "guide"
    reviewer = "reviewer"
    hod = "hod"
    coordinator = "coordinator"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    roll_no: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    department: Mapped[str] = mapped_column(String(100), default="CSE")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Reviewer "slot" accounts (Reviewer 1, Reviewer 2, ...) are shared logins the
    # coordinator reassigns to different real staff per review round, with a
    # freshly generated password each time — see app/routers/coordinator.py.
    is_reviewer_slot: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="student", foreign_keys="Project.student_id"
    )
    guided_projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="guide", foreign_keys="Project.assigned_guide_id"
    )
    reviewed_projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="reviewer", foreign_keys="Project.assigned_reviewer_id"
    )
    notes: Mapped[list["InternalNote"]] = relationship("InternalNote", back_populates="author_user")
    appeals: Mapped[list["Appeal"]] = relationship("Appeal", back_populates="student")
    rubrics: Mapped[list["Rubric"]] = relationship("Rubric", back_populates="creator")
