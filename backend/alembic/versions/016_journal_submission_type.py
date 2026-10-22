"""Add 'journal' as a submission type. 'video' stays in the DB enum
(Postgres can't drop enum values) but is no longer accepted on new
uploads — see app/routers/projects.py:upload_project.

Revision ID: 016
Revises: 015
"""

from alembic import op


revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE submissiontype ADD VALUE IF NOT EXISTS 'journal'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enums; leaving 'journal' in place on
    # downgrade is intentional (same precedent as 'coordinator' in 015).
    pass
