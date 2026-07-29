"""Serialization helpers for idm-heatpump-api metadata."""

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


def json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [json_value(item) for item in value]
    return value


def register_metadata(register) -> dict[str, Any]:
    return {
        "name": register.name,
        "address": register.address,
        "datatype": register.datatype.value,
        "size": register.size,
        "register_type": register.register_type.value,
        "unit": register.unit,
        "multiplier": register.multiplier,
        "writable": register.writable,
        "write_class": register.write_class.value,
        "minimum": register.min_val,
        "maximum": register.max_val,
        "enum_options": register.enum_options,
        "supported_models": list(register.supported_models),
        "sentinel_values": list(register.effective_sentinel_values),
        "source": register.source,
        "source_version": register.source_version,
    }
