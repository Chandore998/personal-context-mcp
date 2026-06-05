from sqlalchemy import JSON, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from personal_context_mcp.db.base import Base, TimestampMixin


class TaskOutcome(TimestampMixin, Base):
    __tablename__ = "task_outcomes"
    __table_args__ = (Index("ix_task_outcomes_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, server_default="default")
    task_summary: Mapped[str] = mapped_column(Text, nullable=False)
    final_solution: Mapped[str | None] = mapped_column(Text)
    decisions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    mistakes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    corrections: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    learned_preferences: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source: Mapped[str | None] = mapped_column(String(255))
