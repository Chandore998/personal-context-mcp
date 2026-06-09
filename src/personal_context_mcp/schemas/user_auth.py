from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    expires_at: datetime | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    key_prefix: str
    is_active: bool
    expires_at: datetime | None
    created_at: datetime
    last_seen_at: datetime | None = None
    ip_address: str | None = None


class UserKeyResponse(BaseModel):
    user: UserRead
    api_key: str
    message: str
