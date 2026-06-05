"""add user_id to all tables for per-user data isolation

Revision ID: 20260605_0003
Revises: 20260530_0002
Create Date: 2026-06-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260605_0003"
down_revision: str | None = "20260530_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ["memories", "user_profiles", "work_styles", "task_outcomes"]


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("user_id", sa.String(255), nullable=True))
        op.execute(f"UPDATE {table} SET user_id = 'default'")  # noqa: S608
        op.alter_column(table, "user_id", existing_type=sa.String(255), nullable=False)
        op.create_index(f"ix_{table}_user_id", table, ["user_id"])


def downgrade() -> None:
    for table in _TABLES:
        op.drop_index(f"ix_{table}_user_id", table_name=table)
        op.drop_column(table, "user_id")
