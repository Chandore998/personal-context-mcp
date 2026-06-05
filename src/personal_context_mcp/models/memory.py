from sqlalchemy import JSON, Enum, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from personal_context_mcp.db.base import Base, TimestampMixin
from personal_context_mcp.models.enums import MemoryType


class Memory(TimestampMixin, Base):
    __tablename__ = "memories"
    __table_args__ = (Index("ix_memories_user_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, server_default="default")
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_type: Mapped[MemoryType] = mapped_column(Enum(MemoryType), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source: Mapped[str | None] = mapped_column(String(255))
    importance: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    semantic_score: Mapped[float | None] = mapped_column(Float)
