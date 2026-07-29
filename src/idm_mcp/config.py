from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """IDM connection, discovery, write policy, and MCP transport settings."""

    model_config = SettingsConfigDict(env_prefix="IDM_", env_file=".env", extra="ignore")
    host: str = ""
    port: int = Field(502, ge=1, le=65535)
    unit_id: int = Field(1, ge=1, le=247)
    timeout: float = Field(5, gt=0, le=60)
    auto_detect: bool = True
    allow_writes: bool = False
    writable_entities: frozenset[str] = frozenset()

    @field_validator("writable_entities", mode="before")
    @classmethod
    def parse_names(cls, value):
        if isinstance(value, str):
            return frozenset(item.strip() for item in value.split(",") if item.strip())
        return value


class McpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MCP_", env_file=".env", extra="ignore")
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = Field(8100, ge=1, le=65535)
    path: str = "/mcp"


@lru_cache
def get_settings() -> Settings:
    return Settings()
