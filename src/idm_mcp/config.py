from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IDM_", env_file=".env", extra="ignore")
    host: str = ""
    port: int = Field(502, ge=1, le=65535)
    unit_id: int = Field(1, ge=0, le=247)
    timeout: float = Field(5, gt=0, le=60)
    register_map: Path | None = None
    allow_writes: bool = False
    writable_addresses: frozenset[int] = frozenset()

    @field_validator("writable_addresses", mode="before")
    @classmethod
    def parse_addresses(cls, value):
        if isinstance(value, str):
            return frozenset(int(item.strip(), 0) for item in value.split(",") if item.strip())
        return value


@lru_cache
def get_settings():
    return Settings()
