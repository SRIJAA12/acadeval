"""Live scoring telemetry + continuous evaluation (benchmark/graph-integrity/faculty-agreement).

Adds: pipelinestatus.failed, projects.pipeline_error, faculty_evaluations.method_fingerprint,
evaluation_reports.similarity_external made nullable (it was silently defaulting to 0.0 —
"not computed" must not look identical to "0% external risk"); new tables scoring_telemetry,
eval_runs, eval_metrics, project_embeddings.

Revision ID: 012
Revises: 011
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # New enum value. Must run in its own statement; Postgres forbids using a
    # just-added enum value inside the same transaction, but we only add it here.
    op.execute("ALTER TYPE pipelinestatus ADD VALUE IF NOT EXISTS 'failed'")

    op.add_column("projects", sa.Column("pipeline_error", sa.Text(), nullable=True))
    op.add_column("faculty_evaluations", sa.Column("method_fingerprint", sa.String(64), nullable=True))
    op.alter_column("evaluation_reports", "similarity_external", existing_type=sa.Float(), nullable=True)

    op.create_table(
        "scoring_telemetry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("run_id", sa.String(64), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("failed_stage", sa.String(50), nullable=True),
        sa.Column("error_class", sa.String(200), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stage_ms", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("total_ms", sa.Float(), nullable=True),
        sa.Column("method_fingerprint", sa.String(64), nullable=True),
        sa.Column("versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("novelty_score", sa.Float(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("top1_similarity", sa.Float(), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=True),
        sa.Column("invariants", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("invariants_passed", sa.Boolean(), nullable=True),
        sa.Column("explanation_claims", sa.Integer(), nullable=True),
        sa.Column("explanation_backed", sa.Integer(), nullable=True),
        sa.Column("forbidden_claims", sa.Integer(), nullable=True),
        sa.Column("evidence_quality", sa.String(20), nullable=True),
        sa.Column("entity_count", sa.Integer(), nullable=True),
        sa.Column("corpus_key_coverage", sa.Float(), nullable=True),
        sa.Column("repeat_checked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("repeat_max_abs_delta", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_scoring_telemetry_project_id", "scoring_telemetry", ["project_id"])
    op.create_index("ix_scoring_telemetry_method_fingerprint", "scoring_telemetry", ["method_fingerprint"])
    op.create_index("ix_scoring_telemetry_created_at", "scoring_telemetry", ["created_at"])

    op.create_table(
        "eval_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("trigger", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("method_fingerprint", sa.String(64), nullable=True),
        sa.Column("versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("benchmark_version", sa.String(64), nullable=True),
        sa.Column("n_cases", sa.Integer(), nullable=True),
        sa.Column("similarity_weights", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(64), nullable=True),
    )
    op.create_index("ix_eval_runs_method_fingerprint", "eval_runs", ["method_fingerprint"])
    op.create_index("ix_eval_runs_started_at", "eval_runs", ["started_at"])

    op.create_table(
        "eval_metrics",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric", sa.String(60), nullable=False),
        sa.Column("variant", sa.String(30), nullable=False, server_default="combined"),
        sa.Column("slice", sa.String(60), nullable=False, server_default="all"),
        sa.Column("value", sa.Float(), nullable=True),
        sa.Column("n", sa.Integer(), nullable=True),
        sa.Column("ci_low", sa.Float(), nullable=True),
        sa.Column("ci_high", sa.Float(), nullable=True),
        sa.Column("target", sa.Float(), nullable=True),
        sa.Column("target_op", sa.String(4), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_eval_metrics_metric_variant_slice_created",
        "eval_metrics", ["metric", "variant", "slice", "created_at"],
    )

    op.create_table(
        "project_embeddings",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), primary_key=True),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("vector", sa.LargeBinary(), nullable=False),
        sa.Column("dim", sa.Integer(), nullable=False, server_default="384"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("project_embeddings")
    op.drop_index("ix_eval_metrics_metric_variant_slice_created", table_name="eval_metrics")
    op.drop_table("eval_metrics")
    op.drop_index("ix_eval_runs_started_at", table_name="eval_runs")
    op.drop_index("ix_eval_runs_method_fingerprint", table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_index("ix_scoring_telemetry_created_at", table_name="scoring_telemetry")
    op.drop_index("ix_scoring_telemetry_method_fingerprint", table_name="scoring_telemetry")
    op.drop_index("ix_scoring_telemetry_project_id", table_name="scoring_telemetry")
    op.drop_table("scoring_telemetry")
    op.alter_column("evaluation_reports", "similarity_external", existing_type=sa.Float(), nullable=False, server_default="0.0")
    op.drop_column("faculty_evaluations", "method_fingerprint")
    op.drop_column("projects", "pipeline_error")
    # Postgres has no DROP VALUE for enums; leaving 'failed' in place on downgrade is intentional.
