"""initial tables

Revision ID: 20260529_0001
Revises:
Create Date: 2026-05-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260529_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

memory_type_enum = sa.Enum(
    "TASK_SUMMARY",
    "PROJECT_SUMMARY",
    "MISTAKE",
    "CORRECTION",
    "PREFERENCE",
    "DECISION",
    "NOTE",
    name="memorytype",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("primary_skills", sa.JSON(), nullable=False),
        sa.Column("preferred_languages", sa.JSON(), nullable=False),
        sa.Column("preferred_frameworks", sa.JSON(), nullable=False),
        sa.Column("preferred_explanation_style", sa.String(length=255), nullable=True),
        sa.Column("preferred_code_style", sa.String(length=255), nullable=True),
        sa.Column("preferred_architecture_style", sa.String(length=255), nullable=True),
        sa.Column("communication_preferences", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "work_styles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_approach", sa.Text(), nullable=True),
        sa.Column("explanation_preference", sa.String(length=255), nullable=True),
        sa.Column("workflow_patterns", sa.JSON(), nullable=False),
        sa.Column("production_example_preference", sa.String(length=255), nullable=True),
        sa.Column("common_preferences", sa.JSON(), nullable=False),
        sa.Column("common_mistakes_to_avoid", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "memories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("memory_type", memory_type_enum, nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("embedding", sa.JSON(), nullable=True),
        sa.Column("semantic_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "task_outcomes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_summary", sa.Text(), nullable=False),
        sa.Column("final_solution", sa.Text(), nullable=True),
        sa.Column("decisions", sa.JSON(), nullable=False),
        sa.Column("mistakes", sa.JSON(), nullable=False),
        sa.Column("corrections", sa.JSON(), nullable=False),
        sa.Column("learned_preferences", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("task_outcomes")
    op.drop_table("memories")
    op.drop_table("work_styles")
    op.drop_table("user_profiles")
    memory_type_enum.drop(op.get_bind(), checkfirst=True)
