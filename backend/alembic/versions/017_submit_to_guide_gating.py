"""Submit-to-Guide / Ready-for-Review gating: a student now controls when
their guide can see a project at all (score must be >30), and can flag a
project as ready for the Coordinator to pick for a review round. Backfills
existing assigned projects so nothing already visible goes dark.

Revision ID: 017
Revises: 016
"""

from alembic import op
import sqlalchemy as sa


revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("guide_submitted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("reviewer_ready_at", sa.DateTime(timezone=True), nullable=True))

    # Backfill: any project that already has a guide/reviewer assigned (from
    # roster upload, HOD assignment, or round assignment in prior sessions)
    # keeps working exactly as before — no retroactive "re-submit" needed.
    op.execute(
        "UPDATE projects SET guide_submitted_at = submitted_on WHERE assigned_guide_id IS NOT NULL"
    )
    op.execute(
        "UPDATE projects SET reviewer_ready_at = submitted_on WHERE assigned_reviewer_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("projects", "reviewer_ready_at")
    op.drop_column("projects", "guide_submitted_at")
