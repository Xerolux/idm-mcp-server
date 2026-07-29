import json

from mcp.server.fastmcp import FastMCP

from .client import IdmClient
from .config import get_settings
from .models import Registry
from .service import IdmService

mcp = FastMCP("IDM Heat Pump")
_service = None


def service():
    global _service
    if _service is None:
        settings = get_settings()
        _service = IdmService(settings, Registry.load(settings.register_map), IdmClient(settings))
    return _service


@mcp.tool()
def list_entities() -> str:
    """List all configured heat-pump entities."""
    return json.dumps(service().list_entities(), ensure_ascii=False)


@mcp.tool()
async def read_entity(name: str) -> str:
    """Read a configured entity by name."""
    return json.dumps(await service().read_entity(name), ensure_ascii=False)


@mcp.tool()
async def write_entity(name: str, value: float) -> str:
    """Write an explicitly allowed entity; writes are disabled by default."""
    return json.dumps(await service().write_entity(name, value), ensure_ascii=False)


@mcp.resource("idm://entities")
def entities_resource() -> str:
    return json.dumps(service().list_entities(), ensure_ascii=False)


@mcp.resource("idm://entities/{name}")
async def entity_resource(name: str) -> str:
    return json.dumps(await service().read_entity(name), ensure_ascii=False)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
