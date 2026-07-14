"""Create users and link Script Chat threads to them.

Revision ID: 20260711_02
Revises: 20260710_01
Create Date: 2026-07-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260711_02"
down_revision: Union[str, Sequence[str], None] = "20260710_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("picture", sa.Text(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint(
            "provider",
            "provider_subject",
            name="uq_users_provider_subject",
        ),
    )

    # Existing thread ownership used normalized email strings. Preserve those
    # records as legacy identities; the next Google login upgrades each row with
    # Google's stable provider subject and current profile data.
    op.execute(
        """
        INSERT INTO users (provider, provider_subject, email)
        SELECT 'legacy', LOWER(user_id), LOWER(user_id)
        FROM script_chat_threads
        GROUP BY LOWER(user_id)
        ON CONFLICT (email) DO NOTHING
        """
    )

    op.add_column(
        "script_chat_threads",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        """
        UPDATE script_chat_threads AS thread
        SET owner_user_id = users.id
        FROM users
        WHERE users.email = LOWER(thread.user_id)
        """
    )
    op.alter_column("script_chat_threads", "owner_user_id", nullable=False)

    op.drop_index("ix_script_chat_threads_user_updated", table_name="script_chat_threads")
    op.drop_column("script_chat_threads", "user_id")
    op.alter_column(
        "script_chat_threads",
        "owner_user_id",
        new_column_name="user_id",
    )
    op.create_foreign_key(
        "fk_script_chat_threads_user_id_users",
        "script_chat_threads",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_script_chat_threads_user_updated",
        "script_chat_threads",
        ["user_id", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_script_chat_threads_user_updated", table_name="script_chat_threads")
    op.drop_constraint(
        "fk_script_chat_threads_user_id_users",
        "script_chat_threads",
        type_="foreignkey",
    )
    op.add_column(
        "script_chat_threads",
        sa.Column("owner_email", sa.String(length=320), nullable=True),
    )
    op.execute(
        """
        UPDATE script_chat_threads AS thread
        SET owner_email = users.email
        FROM users
        WHERE users.id = thread.user_id
        """
    )
    op.alter_column("script_chat_threads", "owner_email", nullable=False)
    op.drop_column("script_chat_threads", "user_id")
    op.alter_column(
        "script_chat_threads",
        "owner_email",
        new_column_name="user_id",
    )
    op.create_index(
        "ix_script_chat_threads_user_updated",
        "script_chat_threads",
        ["user_id", "updated_at"],
    )
    op.drop_table("users")
