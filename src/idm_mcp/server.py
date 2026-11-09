"""MCP server exposing an IDM heat pump via idm-heatpump-api."""

from __future__ import annotations

import json

from idm_heatpump import IdmModbusClient
from mcp.server.fastmcp import FastMCP

from .config import get_settings
from .service import IdmService

mcp = FastMCP("IDM Heat Pump")
_service: IdmService | None = None


def service() -> IdmService:
    global _service
    if _service is None:
        settings = get_settings()
        client = IdmModbusClient(
            host=settings.host or "unconfigured",
            port=settings.port,
            slave_id=settings.slave_id,
            timeout=settings.timeout,
            max_retries=settings.max_retries,
        )
        _service = IdmService(settings, client)
    return _service


def _dump(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


@mcp.tool()
async def detect_model(force: bool = False) -> str:
    """Detect the heat-pump controller model, heating circuits and capabilities.

    Probes the controller over Modbus and rebuilds the datapoint catalogue.
    Use this first when connecting to a plant for the first time.
    """
    return _dump(await service().detect_model(force=force))


@mcp.tool()
async def list_datapoints(writable_only: bool = False, category: str = "") -> str:
    """List all datapoints of the resolved register map.

    Returns key, address, datatype, unit, scale, min/max, write class and
    enum options for every datapoint. Filter with category (substring of the
    key, e.g. "dhw", "hc_a", "energy") or writable_only=true.
    """
    return _dump(service().list_datapoints(writable_only=writable_only, category=category or None))


@mcp.tool()
async def read_datapoint(key: str) -> str:
    """Read one datapoint by key, e.g. "outdoor_temp" or "hc_a_flow_temp"."""
    return _dump(await service().read_datapoint(key))


@mcp.tool()
async def read_all_datapoints(refresh: bool = False) -> str:
    """Read every readable datapoint in one batch (cached for a few seconds).

    Returns a snapshot with model info and all values incl. units and enum
    labels. Set refresh=true to bypass the cache.
    """
    return _dump(await service().read_all(refresh=refresh))


@mcp.tool()
async def validate_write(key: str, value: float | bool) -> str:
    """Validate a planned write without touching the heat pump (dry run).

    Runs the full API validation (min/max, enum, model availability) and
    returns the encoded register plan. Use this before every write.
    """
    return _dump(await service().validate_write(key, value))


@mcp.tool()
async def write_datapoint(key: str, value: float | bool, dry_run: bool = False) -> str:
    """Write a datapoint. Writes are disabled unless explicitly enabled.

    Requires IDM_ALLOW_WRITES=true, the register's write class in
    IDM_WRITE_CLASSES and (if set) the key in IDM_WRITABLE_KEYS. Prefer
    validate_write first; pass dry_run=true to only plan the write.
    """
    return _dump(await service().write_datapoint(key, value, dry_run=dry_run))


@mcp.tool()
async def explain_error_code(code: int) -> str:
    """Explain an IDM controller message number (e.g. from internal_message)."""
    return _dump(service().explain_error_code(code))


@mcp.tool()
async def get_diagnostics() -> str:
    """Report connection state, failed/unsupported registers and cyclic writes."""
    return _dump(await service().diagnostics())


@mcp.resource("idm://model")
async def model_resource() -> str:
    """Resolved controller model and capabilities."""
    return _dump(service().model())


@mcp.resource("idm://datapoints")
async def datapoints_resource() -> str:
    """Complete datapoint catalogue of the resolved register map."""
    return _dump(service().list_datapoints())


@mcp.resource("idm://datapoints/{key}")
async def datapoint_resource(key: str) -> str:
    """Current value of one datapoint."""
    return _dump(await service().read_datapoint(key))


@mcp.resource("idm://values")
async def values_resource() -> str:
    """Cached snapshot of all readable datapoints."""
    return _dump(await service().read_all())


@mcp.resource("idm://diagnostics")
async def diagnostics_resource() -> str:
    """Client diagnostics: connection, failed registers, cyclic writes."""
    return _dump(await service().diagnostics())


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
