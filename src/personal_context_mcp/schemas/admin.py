from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminSignup(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class AdminLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class AdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    status: str
    deleted_at: datetime | None
    is_super_admin: bool
    created_at: datetime
    updated_at: datetime


class AdminAuthResponse(BaseModel):
    message: str
    admin: AdminRead
    access_token: str | None = None
    token_type: str | None = None
    expires_at: datetime | None = None
