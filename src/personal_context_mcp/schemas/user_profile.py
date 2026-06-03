from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserProfileBase(BaseModel):
    name: str | None = None
    role: str | None = None
    primary_skills: list[str] = Field(default_factory=list)
    preferred_languages: list[str] = Field(default_factory=list)
    preferred_frameworks: list[str] = Field(default_factory=list)
    preferred_explanation_style: str | None = None
    preferred_code_style: str | None = None
    preferred_architecture_style: str | None = None
    communication_preferences: str | None = None
    is_active: bool = True


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileRead(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
