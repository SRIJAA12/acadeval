"""Stage 3 versioned evidence-based assessment fields.

Revision ID: 008
Revises: 007
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "evaluation_reports",
        sa.Column("assessment_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "evaluation_reports",
        sa.Column("assessment_method_version", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "evaluation_reports",
        sa.Column("assessment_input_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "evaluation_reports",
        sa.Column("assessment_scored_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("evaluation_reports", "assessment_scored_at")
    op.drop_column("evaluation_reports", "assessment_input_hash")
    op.drop_column("evaluation_reports", "assessment_method_version")
    op.drop_column("evaluation_reports", "assessment_evidence")
