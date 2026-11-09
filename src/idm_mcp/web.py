"""Optional local web supplement (Navigator 10 WebSocket / Navigator 2.0 HTTP).

The web interface provides data the Modbus map does not carry (active
notifications with texts, weather, performance details) and a second write
path for settings. Every web write is gated exactly like the equivalent
Modbus register: the action table below maps each web action to the register
whose write class protects it.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from typing import Any

from idm_heatpump import (
    MODEL_NAVIGATOR_10,
    MODEL_NAVIGATOR_17,
    MODEL_NAVIGATOR_20,
    MODEL_NAVIGATOR_PRO,
    create_optional_navigator10_web_client,
    create_optional_navigator20_web_client,
)

from .config import Settings

#: web action -> (equivalent register for the key allowlist, write class).
WEB_WRITE_ACTIONS: dict[str, tuple[str | None, str]] = {
    "set_system_mode": ("system_mode", "eeprom"),
    "save_dhw_setpoint": ("dhw_setpoint", "eeprom"),
    "acknowledge_notifications": ("error_acknowledge", "write_only"),
    "set_datetime": (None, "volatile"),
}

#: model name -> web client variant (mirrors idm-heatpump-hass).
_MODEL_VARIANTS = {
    MODEL_NAVIGATOR_10: "nav10",
    MODEL_NAVIGATOR_PRO: "nav10",
    MODEL_NAVIGATOR_20: "nav20",
    MODEL_NAVIGATOR_17: None,  # the 1.x family has no local web interface
}


def variant_for_model(model_name: str) -> str | None:
    """Return the web variant implied by the controller model, if any."""
    return _MODEL_VARIANTS.get(model_name)


class WebSupplement:
    """Lazy wrapper around one optional local web client."""

    def __init__(
        self,
        settings: Settings,
        model_name: str,
        gate: Callable[[str], None],
        client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.settings = settings
        self.model_name = model_name
        self._gate = gate
        self._client_factory = client_factory
        self._client: Any | None = None
        self.variant: str | None = None

    # -- lifecycle ------------------------------------------------------

    def _resolve_variant(self) -> str | None:
        if self.settings.web_variant == "off":
            return None
        if self.settings.web_variant in {"nav10", "nav20"}:
            return self.settings.web_variant
        return variant_for_model(self.model_name)

    def _create_client(self) -> Any | None:
        if self.variant == "nav10":
            return create_optional_navigator10_web_client(
                self.settings.host, self.settings.web_pin, port=self.settings.web_port
            )
        return create_optional_navigator20_web_client(self.settings.host, self.settings.web_pin)

    def client(self) -> Any | None:
        """Return the connected-on-demand web client, or None when disabled."""
        if self._client is None:
            self.variant = self._resolve_variant()
            if self.variant is None or not self.settings.web_pin.strip():
                return None
            factory = self._client_factory or self._create_client
            self._client = factory()
            if self._client is None:
                return None
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None

    def _require_client(self, action: str) -> Any:
        client = self.client()
        if client is None:
            reason = (
                "web supplement is disabled for this controller"
                if self.variant is None
                else "IDM_WEB_PIN is not configured"
            )
            raise RuntimeError(f"web action {action!r} unavailable: {reason}")
        return client

    def _gated_client(self, action: str) -> Any:
        self._gate(action)
        return self._require_client(action)

    # -- status ---------------------------------------------------------

    async def status(self) -> dict[str, Any]:
        variant = self.settings.web_variant
        if variant in {"", "auto"}:
            variant = variant_for_model(self.model_name) or "none"
        payload: dict[str, Any] = {
            "enabled": bool(self.settings.web_pin.strip()) and variant not in {"none", "off"},
            "variant": variant,
            "pin_configured": bool(self.settings.web_pin.strip()),
            "cached": False,
        }
        client = self.client()
        if client is not None:
            payload["diagnostics"] = asdict(client.diagnostics())
            payload["cached"] = client.get_cached_data() is not None
        return payload

    # -- reads ----------------------------------------------------------

    async def read_data(self) -> dict[str, Any]:
        client = self._require_client("read_data")
        data = await client.read_data()
        return {
            "variant": self.variant,
            "navigator_version": data.navigator_version,
            "software_version": data.software_version,
            "heatpump_model": data.heatpump_model,
            "values": data.simple_values,
            "value_count": len(data.simple_values),
        }

    async def read_cached_data(self) -> dict[str, Any] | None:
        client = self.client()
        if client is None:
            return None
        data = client.get_cached_data()
        if data is None:
            return None
        return {
            "cached": True,
            "navigator_version": data.navigator_version,
            "software_version": data.software_version,
            "heatpump_model": data.heatpump_model,
            "values": data.simple_values,
        }

    async def read_notifications(self) -> dict[str, Any]:
        client = self._require_client("read_notifications")
        if self.variant != "nav10":
            raise RuntimeError(
                f"notifications are only available on Navigator 10 web, not {self.variant!r}"
            )
        notifications = await client.read_notifications()
        return {
            "count": notifications.count,
            "summary": notifications.summary,
            "notifications": [
                {
                    "code": item.code,
                    "message": item.message,
                    "timestamp": item.timestamp,
                    "severity": item.severity,
                    "deferrable": item.deferrable,
                }
                for item in notifications.current
            ],
        }

    # -- writes (gated) -------------------------------------------------

    async def set_system_mode(self, mode: int) -> dict[str, Any]:
        client = self._gated_client("set_system_mode")
        await client.set_system_mode(int(mode))
        return {"action": "set_system_mode", "value": int(mode), "path": "web"}

    async def save_dhw_setpoint(self, celsius: float) -> dict[str, Any]:
        client = self._gated_client("save_dhw_setpoint")
        await client.save_dhw_setpoint(float(celsius))
        return {"action": "save_dhw_setpoint", "value": float(celsius), "path": "web"}

    async def acknowledge_notifications(
        self, code: str = "", *, remind_me_later: bool = False
    ) -> dict[str, Any]:
        client = self._gated_client("acknowledge_notifications")
        if code.strip():
            await client.acknowledge_notification(code.strip(), remind_me_later=remind_me_later)
            return {
                "action": "acknowledge_notification",
                "code": code.strip(),
                "remind_me_later": remind_me_later,
                "path": "web",
            }
        await client.acknowledge_all_notifications()
        return {"action": "acknowledge_all_notifications", "path": "web"}

    async def set_datetime(self, iso: str = "") -> dict[str, Any]:
        client = self._gated_client("set_datetime")
        if iso.strip():
            try:
                value = datetime.fromisoformat(iso.strip())
            except ValueError as exc:
                raise ValueError(
                    f"invalid ISO datetime {iso!r}: use e.g. 2026-11-09T15:30:00"
                ) from exc
        else:
            value = datetime.now().astimezone()
        await client.set_datetime(value)
        return {"action": "set_datetime", "value": value.isoformat(), "path": "web"}
