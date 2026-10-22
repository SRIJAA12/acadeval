"""Widen evaluation_reports.grade from varchar(5) to varchar(50).

assessment_engine.grade_for() returns "C / Requires Improvement" (24 chars)
for scores below 70, and the model already declares String(50), but
migration 001 created the column as String(5). Any submission scoring under
70 therefore failed score_and_report with StringDataRightTruncation and
never left the "processing" state.

Revision ID: 011
Revises: 008
"""

from alembic import op
import sqlalchemy as sa


revision = "011"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "evaluation_reports",
        "grade",
        existing_type=sa.String(5),
        type_=sa.String(50),
        existing_nullable=False,
        existing_server_default="",
    )


def downgrade() -> None:
    op.alter_column(
        "evaluation_reports",
        "grade",
        existing_type=sa.String(50),
        type_=sa.String(5),
        existing_nullable=False,
        existing_server_default="",
    )
