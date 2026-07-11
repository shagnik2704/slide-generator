"""Create application-owned Script Chat thread metadata.

Revision ID: 20260710_01
Revises:
Create Date: 2026-07-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260710_01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("script_chat_threads"):
        op.create_table(
            "script_chat_threads",
            sa.Column("thread_id", sa.String(length=255), primary_key=True),
            sa.Column("user_id", sa.String(length=320), nullable=False),
            sa.Column("title", sa.Text(), nullable=True),
            sa.Column("outline_preview", sa.Text(), nullable=True),
            sa.Column("foss_name", sa.Text(), nullable=True),
            sa.Column("current_stage", sa.String(length=64), nullable=False, server_default="ingest"),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="created"),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
            sa.CheckConstraint(
                "status IN ('created', 'running', 'awaiting_review', 'completed', 'failed')",
                name="ck_script_chat_threads_status",
            ),
        )
    else:
        column_names = {column["name"] for column in inspector.get_columns("script_chat_threads")}
        for name, column_type in (
            ("title", sa.Text()),
            ("outline_preview", sa.Text()),
            ("archived_at", sa.DateTime(timezone=True)),
        ):
            if name not in column_names:
                op.add_column("script_chat_threads", sa.Column(name, column_type, nullable=True))

        op.execute("UPDATE script_chat_threads SET status = 'running' WHERE status = 'active'")
        op.execute(
            """
            UPDATE script_chat_threads
            SET status = 'failed'
            WHERE status NOT IN ('created', 'running', 'awaiting_review', 'completed', 'failed')
            """
        )

        constraint_names = {
            constraint["name"]
            for constraint in inspector.get_check_constraints("script_chat_threads")
        }
        if "ck_script_chat_threads_status" not in constraint_names:
            op.create_check_constraint(
                "ck_script_chat_threads_status",
                "script_chat_threads",
                "status IN ('created', 'running', 'awaiting_review', 'completed', 'failed')",
            )

    inspector = sa.inspect(bind)
    index_names = {index["name"] for index in inspector.get_indexes("script_chat_threads")}
    if "ix_script_chat_threads_user_updated" not in index_names:
        op.create_index(
            "ix_script_chat_threads_user_updated",
            "script_chat_threads",
            ["user_id", "updated_at"],
        )


def downgrade() -> None:
    op.drop_table("script_chat_threads")
