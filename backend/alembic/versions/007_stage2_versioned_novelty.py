"""Stage 2 versioned novelty evidence and stable graph identities.

Revision ID: 007
Revises: 006
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("graph_ingested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("graph_ingestion_version", sa.String(length=50), nullable=True))

    op.add_column("evaluation_reports", sa.Column("novelty_method_version", sa.String(length=50), nullable=True))
    op.add_column("evaluation_reports", sa.Column("novelty_corpus_version", sa.String(length=64), nullable=True))
    op.add_column("evaluation_reports", sa.Column("novelty_corpus_size", sa.Integer(), nullable=True))
    op.add_column("evaluation_reports", sa.Column("novelty_input_hash", sa.String(length=64), nullable=True))
    op.add_column("evaluation_reports", sa.Column("novelty_scored_at", sa.DateTime(timezone=True), nullable=True))

    # graph_nodes/graph_edges are a derived cache. Clear them once so project
    # nodes can move from title-based identity to immutable source keys without
    # leaving duplicate legacy nodes. They are rebuilt through /graph/rebuild.
    op.execute("TRUNCATE TABLE graph_edges, graph_nodes RESTART IDENTITY CASCADE")
    op.add_column("graph_nodes", sa.Column("source_key", sa.String(length=500), nullable=False))
    op.add_column(
        "graph_edges",
        sa.Column(
            "project_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.drop_constraint("uq_graph_nodes_type_name", "graph_nodes", type_="unique")
    op.create_unique_constraint(
        "uq_graph_nodes_type_source_key",
        "graph_nodes",
        ["node_type", "source_key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_graph_nodes_type_source_key", "graph_nodes", type_="unique")
    op.create_unique_constraint("uq_graph_nodes_type_name", "graph_nodes", ["node_type", "name"])
    op.drop_column("graph_nodes", "source_key")
    op.drop_column("graph_edges", "project_ids")

    op.drop_column("evaluation_reports", "novelty_scored_at")
    op.drop_column("evaluation_reports", "novelty_input_hash")
    op.drop_column("evaluation_reports", "novelty_corpus_size")
    op.drop_column("evaluation_reports", "novelty_corpus_version")
    op.drop_column("evaluation_reports", "novelty_method_version")
    op.drop_column("projects", "graph_ingestion_version")
    op.drop_column("projects", "graph_ingested_at")
