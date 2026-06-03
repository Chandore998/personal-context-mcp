from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from personal_context_mcp.db.base import Base, TimestampMixin


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(255))
    primary_skills: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_languages: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_frameworks: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_explanation_style: Mapped[str | None] = mapped_column(String(255))
    preferred_code_style: Mapped[str | None] = mapped_column(String(255))
    preferred_architecture_style: Mapped[str | None] = mapped_column(String(255))
    communication_preferences: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
