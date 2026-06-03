from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskOutcomeBase(BaseModel):
    task_summary: str
    final_solution: str | None = None
    decisions: list[str] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    corrections: list[str] = Field(default_factory=list)
    learned_preferences: list[str] = Field(default_factory=list)
    source: str | None = None


class TaskOutcomeCreate(TaskOutcomeBase):
    pass


class TaskOutcomeRead(TaskOutcomeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
