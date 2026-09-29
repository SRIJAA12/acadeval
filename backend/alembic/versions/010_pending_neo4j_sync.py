"""Add pending_neo4j_sync column for resilient graph ingestion.

Set when a project's Postgres graph write succeeded but the Neo4j sync
failed (Neo4j down/unreachable). A periodic task retries these so Neo4j
does not silently drift out of date relative to Postgres/CSV.

Revision ID: 010
Revises: 009
"""

from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("pending_neo4j_sync", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("projects", "pending_neo4j_sync")
