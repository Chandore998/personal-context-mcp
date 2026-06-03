from pydantic import BaseModel, Field

from personal_context_mcp.schemas.memory import MemoryRead
from personal_context_mcp.schemas.task_outcome import TaskOutcomeRead
from personal_context_mcp.schemas.user_profile import UserProfileRead
from personal_context_mcp.schemas.work_style import WorkStyleRead


class ContextQuery(BaseModel):
    query: str
    limit: int = Field(default=5, ge=1, le=25)


class RelevantContext(BaseModel):
    query: str
    profile: UserProfileRead | None = None
    work_style: WorkStyleRead | None = None
    memories: list[MemoryRead] = Field(default_factory=list)
    task_outcomes: list[TaskOutcomeRead] = Field(default_factory=list)
    context_summary: str = ""
