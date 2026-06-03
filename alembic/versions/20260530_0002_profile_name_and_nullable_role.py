"""add profile name and nullable role

Revision ID: 20260530_0002
Revises: 20260529_0001
Create Date: 2026-05-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260530_0002"
down_revision: str | None = "20260529_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("name", sa.String(length=255), nullable=True))
    op.alter_column("user_profiles", "role", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column("user_profiles", "role", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("user_profiles", "name")
