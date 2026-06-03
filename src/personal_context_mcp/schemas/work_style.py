from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkStyleBase(BaseModel):
    task_approach: str | None = None
    explanation_preference: str | None = None
    workflow_patterns: list[str] = Field(default_factory=list)
    production_example_preference: str | None = None
    common_preferences: list[str] = Field(default_factory=list)
    common_mistakes_to_avoid: list[str] = Field(default_factory=list)
    is_active: bool = True


class WorkStyleCreate(WorkStyleBase):
    pass


class WorkStyleRead(WorkStyleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
