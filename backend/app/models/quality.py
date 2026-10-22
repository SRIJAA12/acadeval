"""Live telemetry and continuous-evaluation tables (see docs/quality architecture).

scoring_telemetry: one row per Celery scoring run (latency, invariants, evidence).
eval_runs / eval_metrics: time series for the benchmark, graph-integrity and
faculty-agreement checks that run on a schedule or when the scoring method
changes. Every metric is stored separately — never collapsed into one score.
project_embeddings: cached MiniLM vectors so the API can rank comparisons
without loading the model in every process.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ScoringTelemetry(Base):
    """One row per scoring run of task_score_and_report. See app/eval/telemetry.py."""
    __tablename__ = "scoring_telemetry"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # Celery chain root id

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")  # running|ok|insufficient|failed
    failed_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_class: Mapped[str | None] = mapped_column(String(200), nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stage_ms: Mapped[dict] = mapped_column(JSONB, default=dict)   # {"parse_and_classify": 812.3, ...}
    total_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    method_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    versions: Mapped[dict] = mapped_column(JSONB, default=dict)  # {"novelty": "...", "assessment": "...", ...}

    novelty_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    top1_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_duplicate: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    invariants: Mapped[dict] = mapped_column(JSONB, default=dict)  # {"score_in_range": true, ...}
    invariants_passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    explanation_claims: Mapped[int | None] = mapped_column(Integer, nullable=True)
    explanation_backed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    forbidden_claims: Mapped[int | None] = mapped_column(Integer, nullable=True)

    evidence_quality: Mapped[str | None] = mapped_column(String(20), nullable=True)
    entity_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    corpus_key_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)

    repeat_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    repeat_max_abs_delta: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class EvalRun(Base):
    """One execution of a continuous-evaluation job (benchmark / graph integrity / faculty agreement)."""
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)       # benchmark|graph_integrity|faculty_agreement|online_rollup
    trigger: Mapped[str] = mapped_column(String(30), nullable=False)    # schedule|version_change|manual|startup_catchup
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")  # running|ok|failed

    label: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. "baseline-v2.0"
    method_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    versions: Mapped[dict] = mapped_column(JSONB, default=dict)
    benchmark_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    n_cases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    similarity_weights: Mapped[dict] = mapped_column(JSONB, default=dict)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    metrics: Mapped[list["EvalMetric"]] = relationship("EvalMetric", back_populates="run", cascade="all, delete-orphan")


class EvalMetric(Base):
    """One metric value from one EvalRun. Never combine metrics into a single score."""
    __tablename__ = "eval_metrics"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False)

    metric: Mapped[str] = mapped_column(String(60), nullable=False)
    variant: Mapped[str] = mapped_column(String(30), nullable=False, default="combined")  # combined|semantic_only|graph_only|entity_only|token_only|-
    slice: Mapped[str] = mapped_column(String(60), nullable=False, default="all")         # all|simbench|synthetic_holdout|domain:X

    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    target: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_op: Mapped[str | None] = mapped_column(String(4), nullable=True)  # ">=" | "<=" | "=="
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    run: Mapped["EvalRun"] = relationship("EvalRun", back_populates="metrics")


class ProjectEmbedding(Base):
    """Cached MiniLM embedding of a project's title+abstract (semantic similarity channel)."""
    __tablename__ = "project_embeddings"

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    vector: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)  # float32, row-major
    dim: Mapped[int] = mapped_column(Integer, nullable=False, default=384)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
