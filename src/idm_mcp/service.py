"""Service layer bridging MCP tools/resources to idm-heatpump-api.

The service owns the :class:`~idm_heatpump.IdmModbusClient` lifecycle, resolves
the plant model (auto-detect or manual override), exposes the register
catalogue of the matching register map and enforces the local write policy on
top of the API's own write validation.
"""

from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

from idm_heatpump import (
    IdmModbusClient,
    IdmModelInfo,
    RegisterDef,
    WriteClass,
    build_register_map,
    get_error_code_info,
)

from .config import Settings
from .web import WEB_WRITE_ACTIONS, WebSupplement

_CYCLIC_NOTE = (
    "cyclic register: the controller expects the value to be rewritten at least "
    "every 300 s while the demand is active (see API docs on cyclic writes)"
)

#: Seconds before a cyclic write deadline expires at which the poller rewrites it.
_CYCLIC_REFRESH_MARGIN = 30.0


def _serialize_register(reg: RegisterDef) -> dict[str, Any]:
    """Render one register definition as MCP-friendly metadata."""
    return {
        "key": reg.name,
        "address": reg.address,
        "register_type": reg.register_type.value,
        "datatype": reg.datatype.value,
        "unit": reg.unit,
        "scale": reg.multiplier,
        "min": reg.min_val,
        "max": reg.max_val,
        "step": reg.step,
        "writable": reg.writable,
        "write_class": reg.write_class.value,
        "enum_options": reg.enum_options,
        "eeprom_sensitive": reg.eeprom_sensitive,
        "binary": reg.binary,
        "write_only": reg.write_only,
        "supported_models": list(reg.supported_models),
    }


def _serialize_model(model_info: IdmModelInfo, *, detected: bool) -> dict[str, Any]:
    return {
        "model_name": model_info.model_name,
        "detected": detected,
        "active_heating_circuits": list(model_info.active_heating_circuits),
        "zone_modules": model_info.zone_modules,
        "has_solar": model_info.has_solar,
        "has_isc": model_info.has_isc,
        "has_pv": model_info.has_pv,
        "has_cascade": model_info.has_cascade,
        "features": sorted(model_info.features),
        "firmware_version": model_info.firmware_version,
        "is_pro": model_info.is_pro,
    }


class IdmService:
    """High-level operations on one IDM heat pump via idm-heatpump-api."""

    def __init__(self, settings: Settings, client: IdmModbusClient) -> None:
        self.settings = settings
        self.client = client
        self._model_info: IdmModelInfo | None = None
        self._model_detected = False
        self._registers: dict[str, RegisterDef] = {}
        self._snapshot: dict[str, Any] | None = None
        self._snapshot_at: float = 0.0
        self.web: WebSupplement | None = None
        self._cyclic_values: dict[str, Any] = {}
        self.poll_state: dict[str, Any] = {
            "enabled": False,
            "interval": 0.0,
            "poll_count": 0,
            "consecutive_failures": 0,
            "last_poll_at": None,
            "last_ok_at": None,
            "last_error": None,
        }

    # -- lifecycle -----------------------------------------------------

    def _require_host(self) -> None:
        if not self.settings.host:
            raise RuntimeError("IDM_HOST is not configured")

    async def ensure_ready(self) -> None:
        """Connect once and resolve model + register map (idempotent)."""
        if self._model_info is not None:
            return
        self._require_host()
        await self.client.connect()
        if self.settings.model:
            model_info = self._manual_model_info()
            self.client.set_model_info(model_info)
        else:
            model_info = await self.client.detect_model()
            self._model_detected = True
        self._apply_model(model_info)

    def _manual_model_info(self) -> IdmModelInfo:
        circuits = self.settings.circuit_letters or ["A"]
        return IdmModelInfo(
            model_name=self.settings.model,
            active_heating_circuits=circuits,
            zone_modules=self.settings.zone_modules or 0,
            has_solar=False,
            has_isc=False,
            has_pv=False,
            has_cascade=False,
        )

    def _apply_model(self, model_info: IdmModelInfo) -> None:
        self._model_info = model_info
        self._registers = dict(
            build_register_map(model_info, rooms_per_zone=self.settings.rooms_per_zone)
        )
        self.web = WebSupplement(self.settings, model_info.model_name, gate=self._gate_web_write)

    async def detect_model(self, force: bool = False) -> dict[str, Any]:
        """Resolve the plant model (cached) or force a re-detection."""
        if not force:
            await self.ensure_ready()
            return self.model()
        self._require_host()
        await self.client.connect()
        model_info = await self.client.detect_model()
        self._model_detected = True
        self._apply_model(model_info)
        return self.model()

    def model(self) -> dict[str, Any]:
        if self._model_info is None:
            raise RuntimeError("model not resolved yet; call ensure_ready() first")
        return _serialize_model(self._model_info, detected=self._model_detected)

    def _require_register(self, key: str) -> RegisterDef:
        if not self._registers:
            raise RuntimeError("register map not loaded yet; call ensure_ready() first")
        reg = self._registers.get(key)
        if reg is None:
            raise KeyError(f"unknown datapoint {key!r}; use list_datapoints to see valid keys")
        return reg

    # -- catalogue -----------------------------------------------------

    def list_datapoints(
        self, *, writable_only: bool = False, category: str | None = None
    ) -> list[dict[str, Any]]:
        """List register metadata for the resolved register map."""
        items = []
        for key, reg in sorted(self._registers.items()):
            if writable_only and not reg.writable:
                continue
            if category and category.lower() not in key.lower():
                continue
            items.append(_serialize_register(reg))
        return items

    # -- reads ---------------------------------------------------------

    async def read_datapoint(self, key: str) -> dict[str, Any]:
        """Read one datapoint and decode it with unit and enum label."""
        await self.ensure_ready()
        reg = self._require_register(key)
        if reg.write_only:
            raise ValueError(
                f"{key!r} is write-only (trigger) and cannot be read; use write_datapoint"
            )
        value = await self.client.read_value(key)
        result: dict[str, Any] = {
            "key": key,
            "value": value,
            "unit": reg.unit,
        }
        if reg.enum_options is not None:
            result["enum_options"] = reg.enum_options
            if isinstance(value, int) and value in reg.enum_options:
                result["enum_label"] = reg.enum_options[value]
        if isinstance(value, float) and value in reg.effective_sentinel_values:
            result["unused"] = True
        return result

    async def read_all(self, *, refresh: bool = False) -> dict[str, Any]:
        """Batch-read every readable datapoint (cached for cache_ttl seconds)."""
        await self.ensure_ready()
        now = time.monotonic()
        if (
            not refresh
            and self._snapshot is not None
            and self.settings.cache_ttl > 0
            and now - self._snapshot_at < self.settings.cache_ttl
        ):
            return {**self._snapshot, "cached": True}

        readable = [reg for reg in self._registers.values() if not reg.write_only]
        values = await self.client.read_batch(readable)
        rendered: dict[str, Any] = {}
        for key, value in values.items():
            reg = self._registers[key]
            entry: dict[str, Any] = {"value": value}
            if reg.unit:
                entry["unit"] = reg.unit
            if reg.enum_options is not None and isinstance(value, int):
                entry["enum"] = reg.enum_options.get(value)
            rendered[key] = entry

        snapshot = {
            "model": self.model(),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "value_count": len(rendered),
            "failed_count": len(readable) - len(rendered),
            "values": rendered,
            "cached": False,
        }
        self._snapshot = snapshot
        self._snapshot_at = now
        return dict(snapshot)

    # -- writes --------------------------------------------------------

    def _gate_write(self, key: str, reg: RegisterDef) -> None:
        """Enforce the local write policy (device-independent part)."""
        if not reg.writable:
            raise PermissionError(
                f"datapoint {key!r} is read-only (write_class={reg.write_class.value})"
            )
        if not self.settings.allow_writes:
            raise PermissionError(
                "writes are disabled: set IDM_ALLOW_WRITES=true and configure "
                "IDM_WRITE_CLASSES to enable controlled writes"
            )
        allowed = {str(item) for item in self.settings.write_classes}
        if reg.write_class.value not in allowed:
            raise PermissionError(
                f"write class {reg.write_class.value!r} of {key!r} is not allowed; "
                f"IDM_WRITE_CLASSES currently allows {sorted(allowed)}"
            )
        if self.settings.writable_keys and key not in self.settings.writable_keys:
            raise PermissionError(f"datapoint {key!r} is not in the IDM_WRITABLE_KEYS allowlist")

    def _gate_web_write(self, action: str) -> None:
        """Gate a web write through the equivalent register's write class."""
        register_key, write_class = WEB_WRITE_ACTIONS[action]
        if not self.settings.allow_writes:
            raise PermissionError(
                "writes are disabled: set IDM_ALLOW_WRITES=true and configure "
                "IDM_WRITE_CLASSES to enable controlled writes"
            )
        allowed = {str(item) for item in self.settings.write_classes}
        if write_class not in allowed:
            raise PermissionError(
                f"web action {action!r} requires write class {write_class!r}; "
                f"IDM_WRITE_CLASSES currently allows {sorted(allowed)}"
            )
        if (
            register_key is not None
            and self.settings.writable_keys
            and register_key not in self.settings.writable_keys
        ):
            raise PermissionError(
                f"register {register_key!r} (equivalent of {action!r}) is not in "
                "the IDM_WRITABLE_KEYS allowlist"
            )

    async def validate_write(self, key: str, value: Any) -> dict[str, Any]:
        """Simulate a write and return the encoded plan without touching the device."""
        await self.ensure_ready()
        reg = self._require_register(key)
        if not reg.writable:
            raise PermissionError(
                f"datapoint {key!r} is read-only (write_class={reg.write_class.value})"
            )
        result = self.client.simulate_write(key, value)
        return self._write_result(key, result, planned_only=True)

    async def write_datapoint(
        self, key: str, value: Any, *, dry_run: bool = False
    ) -> dict[str, Any]:
        """Write a datapoint after local gating and full API validation."""
        if dry_run:
            return await self.validate_write(key, value)
        # Global switch first: reject disabled writes before any device I/O.
        if not self.settings.allow_writes:
            raise PermissionError(
                "writes are disabled: set IDM_ALLOW_WRITES=true and configure "
                "IDM_WRITE_CLASSES to enable controlled writes"
            )
        await self.ensure_ready()
        reg = self._require_register(key)
        self._gate_write(key, reg)
        try:
            result = await self.client.set_value(key, value)
        except Exception:
            # Invalidate the snapshot so the next read reflects the device state.
            self._snapshot = None
            raise
        if reg.write_class is WriteClass.CYCLIC:
            # Remember the value so the poller can keep the demand alive.
            self._cyclic_values[key] = result.requested_value
        self._snapshot = None
        return self._write_result(key, result, planned_only=False)

    def _write_result(self, key: str, result, *, planned_only: bool) -> dict[str, Any]:
        reg = result.register
        payload: dict[str, Any] = {
            "key": key,
            "value": result.requested_value,
            "unit": reg.unit,
            "write_class": reg.write_class.value,
            "encoded_registers": list(result.encoded_registers),
            "address": reg.address,
            "dry_run": planned_only or result.dry_run,
        }
        if reg.enum_options is not None:
            payload["enum_options"] = reg.enum_options
        if reg.write_class is WriteClass.CYCLIC:
            payload["note"] = _CYCLIC_NOTE
        return payload

    # -- background polling ----------------------------------------------

    async def poll_once(self) -> dict[str, Any]:
        """One poller tick: refresh snapshot and maintain cyclic writes."""
        state = self.poll_state
        state["last_poll_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        try:
            await self.ensure_ready()
            await self.maintain_cyclic_writes()
            snapshot = await self.read_all(refresh=True)
            state["poll_count"] += 1
            state["consecutive_failures"] = 0
            state["last_ok_at"] = state["last_poll_at"]
            state["last_error"] = None
            return snapshot
        except Exception as exc:
            state["consecutive_failures"] += 1
            state["last_error"] = f"{type(exc).__name__}: {exc}"
            raise

    async def maintain_cyclic_writes(self, *, margin: float = _CYCLIC_REFRESH_MARGIN) -> int:
        """Rewrite cyclic demands nearing (or past) their TTL deadline.

        Runs on the poller; values originate from writes made through this
        server instance. Returns the number of rewrites issued.
        """
        if not self._cyclic_values:
            return 0
        now = time.monotonic()
        due = set(self.client.get_expired_cyclic_writes())
        for key, deadline in self.client.get_active_cyclic_writes().items():
            if deadline - now <= margin:
                due.add(key)
        rewritten = 0
        for key in sorted(due):
            value = self._cyclic_values.get(key)
            reg = self._registers.get(key)
            if value is None or reg is None:
                continue
            try:
                await self.client.set_value(key, value)
            except Exception as exc:  # noqa: BLE001 - poller must never crash
                self.poll_state["last_error"] = f"cyclic rewrite {key!r} failed: {exc}"
                continue
            rewritten += 1
        return rewritten

    # -- diagnostics ----------------------------------------------------

    async def diagnostics(self) -> dict[str, Any]:
        """Connection and register health of the underlying API client."""
        await self.ensure_ready()
        diag = self.client.get_diagnostics()
        payload = asdict(diag)
        payload["host"] = self.settings.host
        payload["port"] = self.settings.port
        payload["slave_id"] = self.settings.slave_id
        payload["unsupported_registers"] = list(self.client.get_unsupported_registers())
        payload["active_cyclic_writes"] = self.client.get_active_cyclic_writes()
        payload["expired_cyclic_writes"] = sorted(self.client.get_expired_cyclic_writes())
        payload["maintained_cyclic_values"] = dict(self._cyclic_values)
        payload["model"] = self.model()
        payload["datapoint_count"] = len(self._registers)
        if self.web is not None:
            payload["web"] = await self.web.status()
        return payload

    # -- error codes ----------------------------------------------------

    def explain_error_code(self, code: int) -> dict[str, Any]:
        """Explain a controller message number from the vendor database."""
        info = get_error_code_info(code)
        if info is None:
            return {
                "code": code,
                "known": False,
                "hint": "unknown code; 20-999 are controller messages, "
                "10000+ device-side error blocks",
            }
        return {
            "code": info.code,
            "known": True,
            "is_warning": info.is_warning,
            "display_text": info.display_text,
            "component": info.text,
            "error_kind": info.info,
            "user_description": info.user_description,
            "service_description": info.service_description,
        }
