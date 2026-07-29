"""Adapter around the canonical idm-heatpump-api library."""

from idm_heatpump import IdmModbusClient

from .config import Settings


def create_client(settings: Settings) -> IdmModbusClient:
    """Create the shared upstream client used by HASS and this MCP server."""
    if not settings.host:
        raise RuntimeError("IDM_HOST is not configured")
    return IdmModbusClient(
        host=settings.host,
        port=settings.port,
        slave_id=settings.unit_id,
        timeout=settings.timeout,
    )
