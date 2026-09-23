import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String, Float, Boolean, DateTime, ForeignKey, Text, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EvaluationReport(Base):
    __tablename__ = "evaluation_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), unique=True, nullable=False
    )

    # Overall
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    grade: Mapped[str] = mapped_column(String(50), default="")

    # 7 Dimension scores (null for abstract-only where N/A)
    novelty_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    feasibility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completeness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    technical_depth_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    clarity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    similarity_risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    publication_potential_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Similarity
    similarity_internal: Mapped[float] = mapped_column(Float, default=0.0)
    similarity_external: Mapped[float] = mapped_column(Float, default=0.0)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)

    # Qualitative ratings
    feasibility_rating: Mapped[str] = mapped_column(String(20), default="Medium")  # High/Medium/Low
    novelty_verdict: Mapped[str] = mapped_column(String(30), default="Somewhat Novel")

    # JSONB fields — rich structured data
    missing_sections: Mapped[list] = mapped_column(JSONB, default=list)
    writing_quality: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    citations: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    novelty_report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    novelty_method_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    novelty_corpus_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    novelty_corpus_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    novelty_input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    novelty_scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assessment_evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    assessment_method_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    assessment_input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assessment_scored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    strengths: Mapped[list] = mapped_column(JSONB, default=list)
    weaknesses: Mapped[list] = mapped_column(JSONB, default=list)
    improvement_roadmap: Mapped[list] = mapped_column(JSONB, default=list)
    badges: Mapped[list] = mapped_column(JSONB, default=list)
    percentile_ranks: Mapped[dict] = mapped_column(JSONB, default=dict)
    flagging_reasons: Mapped[list] = mapped_column(JSONB, default=list)

    # Internal (faculty-only) fields
    explainability_annotations: Mapped[list] = mapped_column(JSONB, default=list)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="evaluation")
    score_overrides: Mapped[list["ScoreOverrideHistory"]] = relationship(
        "ScoreOverrideHistory", back_populates="report", cascade="all, delete-orphan"
    )


class InternalNote(Base):
    __tablename__ = "internal_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship("Project", back_populates="notes")
    author_user: Mapped["User"] = relationship("User", back_populates="notes")


class ScoreOverrideHistory(Base):
    __tablename__ = "score_override_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evaluation_reports.id"), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    dimension: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[float] = mapped_column(Float, nullable=False)
    new_value: Mapped[float] = mapped_column(Float, nullable=False)
    changed_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    changed_by_name: Mapped[str] = mapped_column(String(200))
    comment: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    report: Mapped["EvaluationReport"] = relationship("EvaluationReport", back_populates="score_overrides")


class HistoricalScore(Base):
    """Stores per-project dimension scores for percentile ranking across semesters."""
    __tablename__ = "historical_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"))
    dimension: Mapped[str] = mapped_column(String(50))
    score: Mapped[float] = mapped_column(Float)
    semester: Mapped[str] = mapped_column(String(20))
    year: Mapped[int] = mapped_column(Integer)


class FacultyEvaluation(Base):
    """Module 7: Ground truth faculty ratings validating system novelty scores."""
    __tablename__ = "faculty_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), index=True)
    evaluator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    faculty_score: Mapped[float] = mapped_column(Float, nullable=False)  # 1..10 scale
    system_score: Mapped[float] = mapped_column(Float, nullable=False)   # 0..100 scale
    score_delta: Mapped[float] = mapped_column(Float, default=0.0)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship("Project")
    evaluator: Mapped["User"] = relationship("User")
