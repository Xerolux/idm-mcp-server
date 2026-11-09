"""Web supplement tests: variant resolution, reads and gated writes."""

from __future__ import annotations

import pytest
from conftest import FakeTransport, attach_fake_web, make_service

from idm_mcp.web import variant_for_model


def test_variant_for_model_mapping():
    assert variant_for_model("Navigator 10") == "nav10"
    assert variant_for_model("Navigator Pro") == "nav10"
    assert variant_for_model("Navigator 2.0") == "nav20"
    assert variant_for_model("Navigator 1.7") is None


async def test_web_disabled_without_pin(fake: FakeTransport):
    service, _ = make_service(fake)
    await service.ensure_ready()
    status = await service.web.status()
    assert status["enabled"] is False
    assert status["pin_configured"] is False
    with pytest.raises(RuntimeError, match="IDM_WEB_PIN"):
        await service.web.read_data()


async def test_read_web_data_and_notifications(fake: FakeTransport):
    service, _ = make_service(fake, web_pin="1234")
    await service.ensure_ready()
    attach_fake_web(service)
    data = await service.web.read_data()
    assert data["values"]["software_version"] == "NAV10_20.24"
    assert data["heatpump_model"] == "Terra MMW 406"
    assert data["variant"] == "nav10"

    notifications = await service.web.read_notifications()
    assert notifications["count"] == 1
    assert notifications["notifications"][0]["code"] == "142"
    assert "Maximaltemperatur" in notifications["summary"]


async def test_web_notifications_not_available_on_nav20(fake: FakeTransport):
    service, _ = make_service(fake, web_pin="1234")
    await service.ensure_ready()
    attach_fake_web(service, variant="nav20")
    with pytest.raises(RuntimeError, match="Navigator 10 web"):
        await service.web.read_notifications()


async def test_web_writes_disabled_by_default(fake: FakeTransport):
    service, _ = make_service(fake, web_pin="1234")
    await service.ensure_ready()
    client = attach_fake_web(service)
    with pytest.raises(PermissionError, match="writes are disabled"):
        await service.web.set_system_mode(1)
    assert client.calls == []


async def test_web_write_requires_matching_write_class(fake: FakeTransport):
    service, _ = make_service(fake, web_pin="1234", allow_writes=True, write_classes="eeprom")
    await service.ensure_ready()
    client = attach_fake_web(service)
    await service.web.set_system_mode(2)
    assert ("set_system_mode", (2,), {}) in client.calls
    with pytest.raises(PermissionError, match="write_only"):
        await service.web.acknowledge_notifications()


async def test_web_write_respects_writable_keys(fake: FakeTransport):
    service, _ = make_service(
        fake,
        web_pin="1234",
        allow_writes=True,
        write_classes="eeprom",
        writable_keys="dhw_setpoint",
    )
    await service.ensure_ready()
    client = attach_fake_web(service)
    await service.web.save_dhw_setpoint(52.0)
    assert ("save_dhw_setpoint", (52.0,), {}) in client.calls
    with pytest.raises(PermissionError, match="system_mode"):
        await service.web.set_system_mode(1)


async def test_web_set_datetime_needs_volatile(fake: FakeTransport):
    service, _ = make_service(fake, web_pin="1234", allow_writes=True, write_classes="eeprom")
    await service.ensure_ready()
    client = attach_fake_web(service)
    with pytest.raises(PermissionError, match="volatile"):
        await service.web.set_datetime("2026-11-09T15:30:00")

    service.settings.write_classes = {"eeprom", "volatile"}
    await service.web.set_datetime("2026-11-09T15:30:00")
    assert client.calls[-1][0] == "set_datetime"
    with pytest.raises(ValueError, match="ISO datetime"):
        await service.web.set_datetime("not-a-date")


async def test_web_acknowledge_variants(fake: FakeTransport):
    service, _ = make_service(fake, web_pin="1234", allow_writes=True, write_classes="write_only")
    await service.ensure_ready()
    client = attach_fake_web(service)
    result = await service.web.acknowledge_notifications()
    assert result["action"] == "acknowledge_all_notifications"
    result = await service.web.acknowledge_notifications("142", remind_me_later=True)
    assert result["action"] == "acknowledge_notification"
    assert ("acknowledge_notification", ("142",), {"remind_me_later": True}) in client.calls
