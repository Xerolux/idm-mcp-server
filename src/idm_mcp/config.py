"""Settings for the IDM MCP server.

All values can be provided via environment variables with the ``IDM_`` prefix
or via an ``.env`` file. Comma-separated lists are accepted for
``IDM_WRITE_CLASSES`` and ``IDM_WRITABLE_KEYS``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

#: Write classes the server may ever write; "forbidden" can never be allowed.
VALID_WRITE_CLASSES = frozenset({"volatile", "cyclic", "eeprom", "write_only"})

#: Friendly aliases for the model names used by idm-heatpump-api.
MODEL_ALIASES = {
    "navigator10": "Navigator 10",
    "navigator 10": "Navigator 10",
    "navigator2": "Navigator 2.0",
    "navigator 2.0": "Navigator 2.0",
    "navigator20": "Navigator 2.0",
    "navigator 20": "Navigator 2.0",
    "navigatorpro": "Navigator Pro",
    "navigator pro": "Navigator Pro",
    "navigator17": "Navigator 1.7",
    "navigator 1.7": "Navigator 1.7",
}


def normalize_model_name(value: str) -> str:
    """Map a user-supplied model alias to the API's canonical model name."""
    key = value.strip().lower()
    if not key:
        return ""
    return MODEL_ALIASES.get(key, value.strip())


class Settings(BaseSettings):
    """Runtime configuration of the MCP server."""

    model_config = SettingsConfigDict(env_prefix="IDM_", env_file=".env", extra="ignore")

    host: str = ""
    port: int = Field(502, ge=1, le=65535)
    slave_id: int = Field(1, ge=1, le=247)
    timeout: float = Field(10.0, gt=0, le=60)
    max_retries: int = Field(3, ge=1, le=10)

    # Empty model = auto-detect via IdmModbusClient.detect_model(). A manual
    # model skips detection; heating_circuits then defaults to ["A"].
    model: str = ""
    heating_circuits: str = ""
    zone_modules: int | None = None
    rooms_per_zone: int = Field(6, ge=1, le=8)

    # Write safety: writes require ALL of the following.
    # 1. IDM_ALLOW_WRITES=true
    # 2. the register's write class is listed in IDM_WRITE_CLASSES
    # 3. if IDM_WRITABLE_KEYS is non-empty, the register key is listed there
    # On top, idm-heatpump-api validates min/max, enums, model availability
    # and throttles repeated EEPROM writes.
    allow_writes: bool = False
    write_classes: Annotated[frozenset[str], NoDecode] = frozenset()
    writable_keys: Annotated[frozenset[str], NoDecode] = frozenset()

    # Seconds a read_all snapshot stays cached (0 disables caching).
    cache_ttl: float = Field(5.0, ge=0, le=3600)

    @field_validator("model")
    @classmethod
    def _normalize_model(cls, value: str) -> str:
        return normalize_model_name(value)

    @field_validator("write_classes", "writable_keys", mode="before")
    @classmethod
    def _parse_list(cls, value):
        if isinstance(value, str):
            return frozenset(item.strip() for item in value.split(",") if item.strip())
        return value

    @field_validator("write_classes")
    @classmethod
    def _validate_write_classes(cls, value: frozenset[str]) -> frozenset[str]:
        invalid = sorted(value - VALID_WRITE_CLASSES)
        if invalid:
            raise ValueError(
                f"invalid write classes {invalid}; choose from {sorted(VALID_WRITE_CLASSES)}"
            )
        return value

    @field_validator("heating_circuits", mode="before")
    @classmethod
    def _normalize_circuits(cls, value):
        if isinstance(value, str):
            letters = [item.strip().upper() for item in value.split(",") if item.strip()]
            invalid = [c for c in letters if c not in list("ABCDEFG")]
            if invalid:
                raise ValueError(f"invalid heating circuit letters {invalid} (A-G)")
            return ",".join(letters)
        return value

    @property
    def circuit_letters(self) -> list[str]:
        if not self.heating_circuits:
            return []
        return [item for item in self.heating_circuits.split(",") if item]


@lru_cache
def get_settings() -> Settings:
    return Settings()
