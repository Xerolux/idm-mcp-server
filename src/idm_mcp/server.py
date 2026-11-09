"""MCP server exposing an IDM heat pump via idm-heatpump-api."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any

from idm_heatpump import AdaptiveBackoff, IdmModbusClient, PollRateLimiter
from mcp.server.fastmcp import FastMCP

from .config import get_settings
from .service import IdmService
from .web import WebSupplement

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


async def web() -> WebSupplement:
    """Resolve the model and return the web supplement for this plant."""
    await service().ensure_ready()
    assert service().web is not None  # ensured by _apply_model
    return service().web


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


# -- background poller ----------------------------------------------------


async def _poll_loop(interval: float) -> None:
    """Keep the snapshot cache warm and cyclic writes alive."""
    instance = service()
    instance.poll_state.update({"enabled": True, "interval": interval})
    limiter = PollRateLimiter(interval)
    backoff = AdaptiveBackoff()
    while True:
        try:
            await asyncio.sleep(limiter.remaining() or 0.01)
            limiter.mark()
            await instance.poll_once()
            backoff.reset()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - poller must survive any failure
            # Connection trouble: retry with exponential backoff.
            await asyncio.sleep(backoff.next_delay())


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Start the background poller when IDM_POLL_INTERVAL is configured."""
    settings = service().settings
    task: asyncio.Task | None = None
    if settings.poll_interval > 0 and settings.host:
        task = asyncio.create_task(_poll_loop(settings.poll_interval))
    try:
        yield {}
    finally:
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            service().poll_state["enabled"] = False


# The lifespan must be provided at construction time (it is baked into the
# low-level server), so re-create the FastMCP instance with it attached.
mcp = FastMCP("IDM Heat Pump", lifespan=app_lifespan)


# -- Modbus tools ---------------------------------------------------------


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
async def read_datapoints(keys: list[str]) -> str:
    """Read several datapoints in one batch, e.g. ["outdoor_temp", "storage_temp"]."""
    return _dump(await service().read_datapoints(keys))


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
    """Report connection state, poller health, web supplement and cyclic writes."""
    return _dump(await service().diagnostics())


# -- web supplement tools --------------------------------------------------


@mcp.tool()
async def read_web_data() -> str:
    """Read the local web interface supplement (needs IDM_WEB_PIN).

    Returns values the Modbus map does not carry, e.g. software version,
    heat-pump model and infosystem values. Slower than Modbus reads.
    """
    supplement = await web()
    return _dump(await supplement.read_data())


@mcp.tool()
async def read_web_notifications() -> str:
    """Read active controller notifications with message texts (Navigator 10).

    These are the infosystem messages shown on the controller display,
    including remediation-relevant texts.
    """
    supplement = await web()
    return _dump(await supplement.read_notifications())


@mcp.tool()
async def read_web_heating_circuit(hc_id: str) -> str:
    """Read one heating circuit's web state with device-declared ranges.

    Returns operating mode (with the controller's option list), normal/eco
    room setpoints incl. min/max, room temperature, flow setpoint and pump
    state. hc_id is a letter like "A".
    """
    supplement = await web()
    return _dump(await supplement.read_heating_circuit(hc_id))


@mcp.tool()
async def read_web_weather() -> str:
    """Read the controller-side weather forecast (Navigator 10 web).

    Today plus up to six forecast days as served by the controller's own
    myiDM forecast.
    """
    supplement = await web()
    return _dump(await supplement.read_weather())


@mcp.tool()
async def read_web_energyflow() -> str:
    """Read instantaneous power flows: grid, PV and house (Navigator 10 web)."""
    supplement = await web()
    return _dump(await supplement.read_energyflow())


@mcp.tool()
async def web_save_heatingcircuit_parameter(
    parameter_id: str,
    value: float,
    min_value: float | None = None,
    max_value: float | None = None,
) -> str:
    """Write one heating-circuit web parameter (Navigator 10), e.g. HKD04.

    parameter_id follows the HK<x>NN scheme (read_web_heating_circuit shows
    the ids with device-declared ranges). Requires write class "eeprom".
    """
    supplement = await web()
    return _dump(
        await supplement.save_heatingcircuit_parameter(
            parameter_id, value, min_value=min_value, max_value=max_value
        )
    )


@mcp.tool()
async def web_set_system_mode(mode: int) -> str:
    """Set the operating mode via the local web interface.

    Modes: 0 standby, 1 automatic, 2 away, 3 holiday, 4 hot water only,
    5 heating/cooling only. Requires write class "eeprom" (like system_mode).
    """
    supplement = await web()
    return _dump(await supplement.set_system_mode(mode))


@mcp.tool()
async def web_save_dhw_setpoint(celsius: float) -> str:
    """Set the domestic-hot-water setpoint via the local web interface.

    The controller validates against its own declared range. Requires write
    class "eeprom" (like dhw_setpoint).
    """
    supplement = await web()
    return _dump(await supplement.save_dhw_setpoint(celsius))


@mcp.tool()
async def web_acknowledge_notifications(code: str = "", remind_me_later: bool = False) -> str:
    """Acknowledge controller notifications via the local web interface.

    Empty code acknowledges all active notifications. Requires write class
    "write_only" (like error_acknowledge).
    """
    supplement = await web()
    return _dump(await supplement.acknowledge_notifications(code, remind_me_later=remind_me_later))


@mcp.tool()
async def web_set_datetime(iso: str = "") -> str:
    """Set the controller clock via the local web interface.

    Empty iso uses the server's current local time; otherwise pass an ISO
    datetime like 2026-11-09T15:30:00. Requires write class "volatile".
    """
    supplement = await web()
    return _dump(await supplement.set_datetime(iso))


# -- resources --------------------------------------------------------------


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


@mcp.resource("idm://web")
async def web_resource() -> str:
    """Cached web supplement snapshot, if a web client is connected."""
    supplement = await web()
    payload = await supplement.read_cached_data()
    if payload is None:
        payload = await supplement.read_data()
    return _dump(payload)


# -- entry point ------------------------------------------------------------


class BearerAuthMiddleware:
    """Minimal ASGI middleware requiring a static bearer token."""

    def __init__(self, app: Any, token: str) -> None:
        self._app = app
        self._token = token.encode()

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        if scope["type"] == "http":
            headers = {key.lower(): value for key, value in scope.get("headers", [])}
            provided = headers.get(b"authorization", b"")
            expected = b"Bearer " + self._token
            # Constant-time comparison to avoid token probing.
            import hmac

            if not hmac.compare_digest(provided, expected):
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"www-authenticate", b"Bearer"),
                            (b"content-type", b"application/json"),
                        ],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": b'{"error":"unauthorized"}',
                    }
                )
                return
        await self._app(scope, receive, send)


async def _run_http(server: FastMCP, settings: Any) -> None:  # pragma: no cover
    """Serve streamable HTTP, optionally behind the bearer-token check."""
    import uvicorn

    app = server.streamable_http_app()
    if settings.http_token:
        app = BearerAuthMiddleware(app, settings.http_token)  # type: ignore[assignment]
    config = uvicorn.Config(
        app,
        host=settings.http_host,
        port=settings.http_port,
        log_level=server.settings.log_level.lower(),
    )
    await uvicorn.Server(config).serve()


def _apply_http_settings(server: FastMCP, settings: Any) -> None:
    """Configure the streamable-HTTP bind address on a FastMCP instance."""
    server.settings.host = settings.http_host
    server.settings.port = settings.http_port


def main() -> None:
    settings = get_settings()
    if settings.transport == "http":
        _apply_http_settings(mcp, settings)
        import asyncio

        asyncio.run(_run_http(mcp, settings))
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
