import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Enum, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SubmissionType(str, enum.Enum):
    document = "document"
    video = "video"
    abstract = "abstract"


class PipelineStatus(str, enum.Enum):
    uploaded = "uploaded"
    ai_processing = "ai_processing"
    awaiting_review = "awaiting_review"
    reviewed = "reviewed"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    submission_type: Mapped[SubmissionType] = mapped_column(Enum(SubmissionType), nullable=False)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    team_members: Mapped[str | None] = mapped_column(Text, nullable=True)
    batch_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    related_submission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True
    )
    pipeline_status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus), nullable=False, default=PipelineStatus.uploaded
    )
    assigned_guide_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    assigned_reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    is_preliminary: Mapped[bool] = mapped_column(Boolean, default=True)
    submitted_on: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Module 1 output — extracted full text and derived abstract
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Module 3 output — cached entity extraction result so it is never re-computed
    # on every report request. Shape mirrors extractor_service.extract_entities() output.
    extracted_entities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Module 11 — Celery task chain root id; used by /pipeline-status to poll AsyncResult
    celery_task_id: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Relationships
    student: Mapped["User"] = relationship(
        "User", back_populates="projects", foreign_keys=[student_id]
    )
    guide: Mapped["User | None"] = relationship(
        "User", back_populates="guided_projects", foreign_keys=[assigned_guide_id]
    )
    reviewer: Mapped["User | None"] = relationship(
        "User", back_populates="reviewed_projects", foreign_keys=[assigned_reviewer_id]
    )
    files: Mapped[list["ProjectFile"]] = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    evaluation: Mapped["EvaluationReport | None"] = relationship(
        "EvaluationReport", back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    notes: Mapped[list["InternalNote"]] = relationship("InternalNote", back_populates="project", cascade="all, delete-orphan")
    appeals: Mapped[list["Appeal"]] = relationship("Appeal", back_populates="project", cascade="all, delete-orphan")
    viva_sessions: Mapped[list["VivaSession"]] = relationship("VivaSession", back_populates="project", cascade="all, delete-orphan")


class ProjectFile(Base):
    __tablename__ = "project_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    file_type: Mapped[str] = mapped_column(String(50))  # e.g. 'pdf', 'pptx', 'video'
    original_filename: Mapped[str] = mapped_column(String(500))
    storage_path: Mapped[str] = mapped_column(String(1000))
    extracted_text_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship("Project", back_populates="files")
