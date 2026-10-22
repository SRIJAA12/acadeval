"""Real plagiarism checker: text TF-IDF/cosine passage matches and code
k-gram/winnowing fingerprint matches, with a human reviewer-decision field
kept separate from the automated detector score.

Revision ID: 019
Revises: 018
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plagiarism_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("match_type", sa.Enum("text", "code", name="matchtype"), nullable=False),
        sa.Column("source_project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("source_label", sa.String(500), nullable=False),
        sa.Column("candidate_passage", sa.Text(), nullable=False),
        sa.Column("candidate_location", sa.String(300), nullable=True),
        sa.Column("source_passage", sa.Text(), nullable=False),
        sa.Column("source_location", sa.String(300), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column(
            "review_status",
            sa.Enum("unreviewed", "confirmed", "acceptable_overlap", "uncertain", "no_issue", name="reviewstatus"),
            nullable=False, server_default="unreviewed",
        ),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_plagiarism_matches_project_id", "plagiarism_matches", ["project_id"])
    op.create_index("ix_plagiarism_matches_created_at", "plagiarism_matches", ["created_at"])

    op.create_table(
        "code_fingerprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("repo_owner", sa.String(200), nullable=True),
        sa.Column("repo_name", sa.String(200), nullable=True),
        sa.Column("branch", sa.String(100), nullable=True),
        sa.Column("file_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fingerprints", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("fetch_error", sa.Text(), nullable=True),
    )
    op.create_unique_constraint("uq_code_fingerprints_project_id", "code_fingerprints", ["project_id"])


def downgrade() -> None:
    op.drop_table("code_fingerprints")

    op.drop_index("ix_plagiarism_matches_created_at", table_name="plagiarism_matches")
    op.drop_index("ix_plagiarism_matches_project_id", table_name="plagiarism_matches")
    op.drop_table("plagiarism_matches")

    op.execute("DROP TYPE IF EXISTS reviewstatus")
    op.execute("DROP TYPE IF EXISTS matchtype")
