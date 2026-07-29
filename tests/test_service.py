from unittest.mock import AsyncMock, Mock

import pytest
from idm_heatpump import DataType, IdmModelInfo, RegisterDef, RegisterType, WriteSafetyResult

from idm_mcp.config import Settings
from idm_mcp.service import IdmService


@pytest.fixture
def model_info():
    return IdmModelInfo("navigator_10", ["A"], 0, False, False, True, False)


@pytest.fixture
def register():
    return RegisterDef(
        address=42,
        datatype=DataType.FLOAT,
        name="heating_setpoint",
        unit="°C",
        writable=True,
        min_val=10,
        max_val=30,
        register_type=RegisterType.HOLDING,
    )


def make_service(monkeypatch, model_info, register, *, allow=False, names=frozenset()):
    client = Mock()
    client.detect_model = AsyncMock(return_value=model_info)
    client.read_register = AsyncMock(return_value=21.5)
    client.read_batch = AsyncMock(return_value={register.name: 21.5})
    client.set_value = AsyncMock(
        return_value=WriteSafetyResult(register, 21.5, (0, 16748), dry_run=True)
    )
    client.model_info = model_info
    client.get_diagnostics.return_value = Mock()
    monkeypatch.setattr("idm_mcp.service.build_register_map", lambda model_info: {register.name: register})
    settings = Settings(
        host="heatpump", allow_writes=allow, writable_entities=names, auto_detect=True
    )
    return IdmService(settings, client), client


async def test_auto_detects_and_exposes_upstream_metadata(monkeypatch, model_info, register):
    service, client = make_service(monkeypatch, model_info, register)
    entities = await service.list_entities()
    assert entities[0]["datatype"] == "FLOAT"
    assert entities[0]["size"] == 2
    assert entities[0]["write_class"] == "volatile"
    client.detect_model.assert_awaited_once()


async def test_read_uses_upstream_codec(monkeypatch, model_info, register):
    service, client = make_service(monkeypatch, model_info, register)
    assert (await service.read_entity(register.name))["value"] == 21.5
    client.read_register.assert_awaited_once_with(register)


async def test_write_is_disabled_by_default(monkeypatch, model_info, register):
    service, _ = make_service(monkeypatch, model_info, register, names={register.name})
    with pytest.raises(PermissionError, match="disabled"):
        await service.write_entity(register.name, 21.5)


async def test_write_requires_name_allowlist(monkeypatch, model_info, register):
    service, _ = make_service(monkeypatch, model_info, register, allow=True)
    with pytest.raises(PermissionError, match="IDM_WRITABLE_ENTITIES"):
        await service.write_entity(register.name, 21.5)


async def test_write_defaults_to_upstream_dry_run(monkeypatch, model_info, register):
    service, client = make_service(
        monkeypatch, model_info, register, allow=True, names={register.name}
    )
    result = await service.write_entity(register.name, 21.5)
    assert result["dry_run"] is True
    client.set_value.assert_awaited_once_with(register.name, 21.5, dry_run=True)
