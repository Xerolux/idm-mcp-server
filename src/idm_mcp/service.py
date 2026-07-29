from __future__ import annotations

import asyncio
from typing import Any

from idm_heatpump import build_register_map

from .models import json_value, register_metadata


class IdmService:
    """Model-aware MCP business layer backed by idm-heatpump-api."""

    def __init__(self, settings, client):
        self.settings = settings
        self.client = client
        self._registers = {}
        self._init_lock = asyncio.Lock()

    async def initialize(self) -> None:
        if self._registers:
            return
        async with self._init_lock:
            if self._registers:
                return
            if self.settings.auto_detect:
                model_info = await self.client.detect_model()
                self._registers = build_register_map(model_info=model_info)
            else:
                self._registers = build_register_map()

    async def system_info(self) -> dict[str, Any]:
        await self.initialize()
        return {
            "model": json_value(self.client.model_info),
            "diagnostics": json_value(self.client.get_diagnostics()),
            "register_count": len(self._registers),
            "writable_register_count": sum(reg.writable for reg in self._registers.values()),
        }

    async def list_entities(self, writable_only: bool = False) -> list[dict[str, Any]]:
        await self.initialize()
        return [
            register_metadata(reg)
            for reg in self._registers.values()
            if not writable_only or reg.writable
        ]

    def _entity(self, name):
        try:
            return self._registers[name]
        except KeyError as exc:
            raise KeyError(f"unknown entity {name!r}") from exc

    async def read_entity(self, name: str) -> dict[str, Any]:
        await self.initialize()
        reg = self._entity(name)
        value = await self.client.read_register(reg)
        result = {"name": name, "value": json_value(value), "unit": reg.unit}
        if reg.enum_options and isinstance(value, (int, float)):
            result["label"] = reg.enum_options.get(int(value))
        return result

    async def read_entities(self, names: list[str]) -> dict[str, Any]:
        await self.initialize()
        registers = [self._entity(name) for name in names]
        return json_value(await self.client.read_batch(registers))

    async def write_entity(self, name: str, value: Any, dry_run: bool = True) -> dict[str, Any]:
        await self.initialize()
        reg = self._entity(name)
        if not self.settings.allow_writes:
            raise PermissionError("writes are disabled; set IDM_ALLOW_WRITES=true")
        if name not in self.settings.writable_entities:
            raise PermissionError(f"entity {name!r} is not in IDM_WRITABLE_ENTITIES")
        plan = await self.client.set_value(name, value, dry_run=dry_run)
        return {
            "name": name,
            "requested_value": json_value(plan.requested_value),
            "encoded_registers": list(plan.encoded_registers),
            "write_class": reg.write_class.value,
            "dry_run": dry_run,
        }
