from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = Field(default="personal-context-mcp", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/personal_context",
        alias="DATABASE_URL",
    )
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")
    pgvector_dimension: int = Field(default=1536, alias="PGVECTOR_DIMENSION")
    context_memory_limit: int = Field(default=5, alias="CONTEXT_MEMORY_LIMIT")
    context_task_limit: int = Field(default=3, alias="CONTEXT_TASK_LIMIT")
    mcp_server_name: str = Field(default="personal-context-mcp", alias="MCP_SERVER_NAME")
    mcp_transport: str = Field(default="stdio", alias="MCP_TRANSPORT")
    mcp_enable_dns_rebinding_protection: bool = Field(
        default=True,
        alias="MCP_ENABLE_DNS_REBINDING_PROTECTION",
    )
    mcp_allowed_hosts: list[str] = Field(default_factory=list, alias="MCP_ALLOWED_HOSTS")
    mcp_allowed_origins: list[str] = Field(default_factory=list, alias="MCP_ALLOWED_ORIGINS")
    railway_public_domain: str | None = Field(default=None, alias="RAILWAY_PUBLIC_DOMAIN")
    sql_echo: bool = Field(default=False, alias="SQL_ECHO")


    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    @field_validator("mcp_allowed_hosts", "mcp_allowed_origins", mode="before")
    @classmethod
    def split_csv_values(cls, value: str | list[str] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [item.strip() for item in value if item and item.strip()]
        return [item.strip() for item in value.split(",") if item.strip()]

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
