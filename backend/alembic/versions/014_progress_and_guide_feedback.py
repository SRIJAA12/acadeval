"""Progress updates (append-only student log) and guide feedback (informal,
non-final marks — separate from the reviewer's official EvaluationReport).

Revision ID: 014
Revises: 013
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "progress_updates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("author_name", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_progress_updates_project_id", "progress_updates", ["project_id"])
    op.create_index("ix_progress_updates_created_at", "progress_updates", ["created_at"])

    op.create_table(
        "guide_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False, unique=True),
        sa.Column("guide_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("guide_name", sa.String(200), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("guide_feedback")
    op.drop_index("ix_progress_updates_created_at", table_name="progress_updates")
    op.drop_index("ix_progress_updates_project_id", table_name="progress_updates")
    op.drop_table("progress_updates")
