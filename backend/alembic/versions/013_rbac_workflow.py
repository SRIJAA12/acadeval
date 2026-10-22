"""RBAC workflow: rubric versioning, audit log, milestones, project
discussion, and in-app notifications.

Revision ID: 013
Revises: 012
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("rubrics", sa.Column("academic_year", sa.String(20), nullable=True))
    op.add_column("rubrics", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("rubrics", sa.Column("supersedes_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rubrics.id"), nullable=True))

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("actor_name", sa.String(200), nullable=False),
        sa.Column("actor_role", sa.String(20), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"])

    milestone_status = postgresql.ENUM(
        "pending", "submitted", "approved", "revision_requested", name="milestonestatus"
    )
    milestone_status.create(op.get_bind(), checkfirst=True)
    # op.create_table()'s own before_create hook would otherwise try to
    # CREATE TYPE again (ignoring the checkfirst=True above) since it builds
    # its own ENUM reference from the column — create_type=False here tells
    # it the type is already managed.
    milestone_status_col = postgresql.ENUM(
        "pending", "submitted", "approved", "revision_requested", name="milestonestatus", create_type=False
    )

    op.create_table(
        "milestones",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", milestone_status_col, nullable=False, server_default="pending"),
        sa.Column("student_submission", sa.Text(), nullable=True),
        sa.Column("guide_comment", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_milestones_project_id", "milestones", ["project_id"])

    op.create_table(
        "discussion_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("author_name", sa.String(200), nullable=False),
        sa.Column("author_role", sa.String(20), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_by", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_discussion_messages_project_id", "discussion_messages", ["project_id"])
    op.create_index("ix_discussion_messages_created_at", "discussion_messages", ["created_at"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.drop_index("ix_discussion_messages_created_at", table_name="discussion_messages")
    op.drop_index("ix_discussion_messages_project_id", table_name="discussion_messages")
    op.drop_table("discussion_messages")

    op.drop_index("ix_milestones_project_id", table_name="milestones")
    op.drop_table("milestones")
    postgresql.ENUM(name="milestonestatus").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_column("rubrics", "supersedes_id")
    op.drop_column("rubrics", "version")
    op.drop_column("rubrics", "academic_year")
