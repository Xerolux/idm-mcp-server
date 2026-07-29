import argparse
import json
from typing import Any

from fastmcp import FastMCP

from .client import create_client
from .config import McpSettings, get_settings
from .service import IdmService

mcp = FastMCP("IDM Heat Pump")
_service = None


def service():
    global _service
    if _service is None:
        settings = get_settings()
        _service = IdmService(settings, create_client(settings))
    return _service


def _json(value):
    return json.dumps(value, ensure_ascii=False, indent=2)


@mcp.tool(annotations={"readOnlyHint": True})
async def get_system_info() -> str:
    """Detect IDM model, firmware and installed capabilities and return diagnostics."""
    return _json(await service().system_info())


@mcp.tool(annotations={"readOnlyHint": True})
async def list_entities(writable_only: bool = False) -> str:
    """List model-specific IDM registers and their complete upstream metadata."""
    return _json(await service().list_entities(writable_only))


@mcp.tool(annotations={"readOnlyHint": True})
async def read_entity(name: str) -> str:
    """Read and decode a register by its canonical idm-heatpump-api name."""
    return _json(await service().read_entity(name))


@mcp.tool(annotations={"readOnlyHint": True})
async def read_entities(names: list[str]) -> str:
    """Efficiently batch-read several canonical register names."""
    return _json(await service().read_entities(names))


@mcp.tool(annotations={"destructiveHint": True})
async def write_entity(name: str, value: Any, dry_run: bool = True) -> str:
    """Validate or write an allowlisted register. Defaults to a safe dry run."""
    return _json(await service().write_entity(name, value, dry_run))


@mcp.resource("idm://system")
async def system_resource() -> str:
    return _json(await service().system_info())


@mcp.resource("idm://entities")
async def entities_resource() -> str:
    return _json(await service().list_entities())


@mcp.resource("idm://entities/{name}")
async def entity_resource(name: str) -> str:
    return _json(await service().read_entity(name))


def main():
    defaults = McpSettings()
    parser = argparse.ArgumentParser(description="IDM Heat Pump MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default=defaults.transport)
    parser.add_argument("--host", default=defaults.host)
    parser.add_argument("--port", type=int, default=defaults.port)
    parser.add_argument("--path", default=defaults.path)
    args = parser.parse_args()
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="http", host=args.host, port=args.port, path=args.path)


if __name__ == "__main__":
    main()
