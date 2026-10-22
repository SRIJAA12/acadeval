"""Coordinator role + portal: bulk roster allocation, reviewer slot accounts,
scheduled review rounds with independent per-round scores, and progress
update attachments.

Revision ID: 015
Revises: 014
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'coordinator'")

    op.add_column("users", sa.Column("is_reviewer_slot", sa.Boolean(), nullable=False, server_default=sa.false()))

    op.add_column("projects", sa.Column("team_id", sa.String(100), nullable=True))
    op.create_index("ix_projects_team_id", "projects", ["team_id"])

    op.add_column("progress_updates", sa.Column("attachment_path", sa.String(1000), nullable=True))
    op.add_column("progress_updates", sa.Column("attachment_filename", sa.String(500), nullable=True))
    op.add_column("progress_updates", sa.Column("github_url", sa.String(500), nullable=True))

    op.create_table(
        "roster_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("roll_no", sa.String(50), nullable=False),
        sa.Column("student_email", sa.String(255), nullable=True),
        sa.Column("team_id", sa.String(100), nullable=True),
        sa.Column("guide_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("guide_email_raw", sa.String(255), nullable=True),
        sa.Column("domain", sa.String(100), nullable=True),
        sa.Column("is_applied", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("applied_project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("uploaded_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_roster_allocations_roll_no", "roster_allocations", ["roll_no"])
    op.create_index("ix_roster_allocations_created_at", "roster_allocations", ["created_at"])

    op.create_table(
        "review_rounds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scheduled_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_final", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "review_slot_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("review_rounds.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("reviewer_slot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("staff_email", sa.String(255), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("credential_email_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_review_slot_assignments_round_id", "review_slot_assignments", ["round_id"])
    op.create_index("ix_review_slot_assignments_project_id", "review_slot_assignments", ["project_id"])

    op.create_table(
        "round_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("review_rounds.id"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("reviewer_slot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("novelty_score", sa.Float(), nullable=True),
        sa.Column("feasibility_score", sa.Float(), nullable=True),
        sa.Column("completeness_score", sa.Float(), nullable=True),
        sa.Column("technical_depth_score", sa.Float(), nullable=True),
        sa.Column("clarity_score", sa.Float(), nullable=True),
        sa.Column("similarity_risk_score", sa.Float(), nullable=True),
        sa.Column("publication_potential_score", sa.Float(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("grade", sa.String(50), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_round_evaluations_round_id", "round_evaluations", ["round_id"])
    op.create_index("ix_round_evaluations_project_id", "round_evaluations", ["project_id"])
    op.create_unique_constraint("uq_round_evaluations_round_project", "round_evaluations", ["round_id", "project_id"])


def downgrade() -> None:
    op.drop_index("ix_round_evaluations_project_id", table_name="round_evaluations")
    op.drop_index("ix_round_evaluations_round_id", table_name="round_evaluations")
    op.drop_table("round_evaluations")

    op.drop_index("ix_review_slot_assignments_project_id", table_name="review_slot_assignments")
    op.drop_index("ix_review_slot_assignments_round_id", table_name="review_slot_assignments")
    op.drop_table("review_slot_assignments")

    op.drop_table("review_rounds")

    op.drop_index("ix_roster_allocations_created_at", table_name="roster_allocations")
    op.drop_index("ix_roster_allocations_roll_no", table_name="roster_allocations")
    op.drop_table("roster_allocations")

    op.drop_column("progress_updates", "github_url")
    op.drop_column("progress_updates", "attachment_filename")
    op.drop_column("progress_updates", "attachment_path")

    op.drop_index("ix_projects_team_id", table_name="projects")
    op.drop_column("projects", "team_id")

    op.drop_column("users", "is_reviewer_slot")
    # Postgres has no DROP VALUE for enums; leaving 'coordinator' in place on
    # downgrade is intentional (same precedent as pipelinestatus.failed in 012).
