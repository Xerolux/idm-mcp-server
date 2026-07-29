from unittest.mock import AsyncMock

import pytest

from idm_mcp.config import Settings
from idm_mcp.models import Entity, Registry
from idm_mcp.service import IdmService


def make_service(allow=False, addresses=frozenset()):
    entity = Entity(
        name="setpoint", address=42, data_type="int16", scale=0.1, writable=True,
        minimum=10, maximum=30,
    )
    client = AsyncMock()
    settings = Settings(host="heatpump", allow_writes=allow, writable_addresses=addresses)
    return IdmService(settings, Registry({entity.name: entity}), client), client


async def test_read_signed_scaled_value():
    service, client = make_service()
    client.read.return_value = 0xFF9C
    assert (await service.read_entity("setpoint"))["value"] == -10


async def test_write_is_disabled_by_default():
    service, _ = make_service(addresses=frozenset({42}))
    with pytest.raises(PermissionError, match="disabled"):
        await service.write_entity("setpoint", 20)


async def test_write_requires_allowlist_and_encodes():
    service, client = make_service(True, frozenset({42}))
    assert (await service.write_entity("setpoint", 21.5))["raw"] == 215
    client.write.assert_awaited_once_with(42, 215)
    with pytest.raises(ValueError, match="above maximum"):
        await service.write_entity("setpoint", 31)
