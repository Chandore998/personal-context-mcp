from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from personal_context_mcp.db.base import Base, TimestampMixin


class WorkStyle(TimestampMixin, Base):
    __tablename__ = "work_styles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_approach: Mapped[str | None] = mapped_column(Text)
    explanation_preference: Mapped[str | None] = mapped_column(String(255))
    workflow_patterns: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    production_example_preference: Mapped[str | None] = mapped_column(String(255))
    common_preferences: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    common_mistakes_to_avoid: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
