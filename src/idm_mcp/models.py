import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Entity(BaseModel):
    name: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_.-]*$")
    address: int = Field(ge=0, le=65535)
    register_type: Literal["holding", "input"] = "holding"
    data_type: Literal["uint16", "int16"] = "uint16"
    scale: float = 1
    offset: float = 0
    unit: str | None = None
    writable: bool = False
    minimum: float | None = None
    maximum: float | None = None
    description: str | None = None

    @model_validator(mode="after")
    def validate_values(self):
        if self.scale == 0:
            raise ValueError("scale must not be zero")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum must not exceed maximum")
        return self

    def decode(self, raw: int) -> float:
        if self.data_type == "int16" and raw >= 0x8000:
            raw -= 0x10000
        return raw * self.scale + self.offset

    def encode(self, value: float) -> int:
        if self.minimum is not None and value < self.minimum:
            raise ValueError(f"value is below minimum {self.minimum}")
        if self.maximum is not None and value > self.maximum:
            raise ValueError(f"value is above maximum {self.maximum}")
        raw = round((value - self.offset) / self.scale)
        low, high = (-32768, 32767) if self.data_type == "int16" else (0, 65535)
        if not low <= raw <= high:
            raise ValueError(f"encoded value is outside {self.data_type}")
        return raw & 0xFFFF


@dataclass(frozen=True)
class Registry:
    entities: dict[str, Entity]

    @classmethod
    def load(cls, path: Path | None):
        if path is None:
            return cls({})
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("entities", data) if isinstance(data, dict) else data
        parsed = [Entity.model_validate(item) for item in items]
        if len({item.name for item in parsed}) != len(parsed):
            raise ValueError("entity names must be unique")
        return cls({item.name: item for item in parsed})
