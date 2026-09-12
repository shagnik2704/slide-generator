"""Add user_activities table for tracking all platform workflows.

Revision ID: 20260912_04
Revises: 20260711_03
Create Date: 2026-09-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260912_04"
down_revision: Union[str, Sequence[str], None] = "20260711_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_activities",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_activities_user_id_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_user_activities_created_at",
        "user_activities",
        ["created_at"],
    )
    op.create_index(
        "ix_user_activities_user_created",
        "user_activities",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_user_activities_type_created",
        "user_activities",
        ["activity_type", "created_at"],
    )

    # Grant read access to grafana_ro if the role exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'grafana_ro') THEN
                GRANT SELECT ON user_activities TO grafana_ro;
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.drop_index("ix_user_activities_type_created", table_name="user_activities")
    op.drop_index("ix_user_activities_user_created", table_name="user_activities")
    op.drop_index("ix_user_activities_created_at", table_name="user_activities")
    op.drop_table("user_activities")
