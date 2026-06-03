from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from personal_context_mcp.models.enums import MemoryType


class MemoryBase(BaseModel):
    title: str
    content: str
    memory_type: MemoryType
    tags: list[str] = Field(default_factory=list)
    source: str | None = None
    importance: int = Field(default=1, ge=1, le=5)
    embedding: list[float] | None = None
    semantic_score: float | None = None


class MemoryCreate(MemoryBase):
    pass


class MemoryRead(MemoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class MemorySearchQuery(BaseModel):
    query: str
    tags: list[str] = Field(default_factory=list)
    memory_types: list[MemoryType] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=25)
