"""Stage 1 project metadata, batch tracking, and persisted novelty report.

Revision ID: 006
Revises: 005
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("team_members", sa.Text(), nullable=True))
    op.add_column("projects", sa.Column("batch_id", sa.String(length=36), nullable=True))
    op.create_index("ix_projects_batch_id", "projects", ["batch_id"], unique=False)
    op.add_column(
        "evaluation_reports",
        sa.Column("novelty_report", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.execute(
        """
        DELETE FROM graph_edges newer
        USING graph_edges older
        WHERE newer.id > older.id
          AND newer.from_node = older.from_node
          AND newer.to_node = older.to_node
          AND newer.relationship = older.relationship
        """
    )
    op.create_unique_constraint(
        "uq_graph_edges_identity",
        "graph_edges",
        ["from_node", "to_node", "relationship"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_graph_edges_identity", "graph_edges", type_="unique")
    op.drop_column("evaluation_reports", "novelty_report")
    op.drop_index("ix_projects_batch_id", table_name="projects")
    op.drop_column("projects", "batch_id")
    op.drop_column("projects", "team_members")
