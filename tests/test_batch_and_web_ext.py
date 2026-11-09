"""Batch reads and the extended web supplement surface."""

from __future__ import annotations

import pytest
from conftest import FakeTransport, attach_fake_web, make_service


async def test_read_datapoints_batch(fake: FakeTransport):
    service, _ = make_service(fake)
    result = await service.read_datapoints(["outdoor_temp", "storage_temp", "system_mode"])
    assert result["requested"] == 3
    assert result["value_count"] == 3
    assert result["values"]["outdoor_temp"]["value"] == pytest.approx(12.5)
    assert result["values"]["storage_temp"]["unit"] == "°C"
    assert "enum" in result["values"]["system_mode"]


async def test_read_datapoints_rejects_unknown_and_write_only(fake: FakeTransport):
    service, _ = make_service(fake)
    with pytest.raises(KeyError, match="unknown datapoint"):
        await service.read_datapoints(["outdoor_temp", "nope"])
    with pytest.raises(ValueError, match="write-only"):
        await service.read_datapoints(["error_acknowledge"])
    with pytest.raises(ValueError, match="keys must not be empty"):
        await service.read_datapoints([])


async def test_read_web_heating_circuit(fake: FakeTransport):
    service, _ = make_service(fake, web_pin="1234")
    await service.ensure_ready()
    client = attach_fake_web(service)
    circuit = await service.web.read_heating_circuit("a")
    assert circuit["hc_id"] == "A"
    assert circuit["mode"]["options"][1]["name"] == "Automatik"
    assert circuit["setpoint_normal"]["parameter_id"] == "HKA04"
    assert circuit["setpoint_normal"]["min"] == 5.0
    assert circuit["available_circuits"] == ["A"]
    assert ("read_heatingcircuit", ("a",), {}) in client.calls


async def test_read_web_weather_and_energyflow(fake: FakeTransport):
    service, _ = make_service(fake, web_pin="1234")
    await service.ensure_ready()
    attach_fake_web(service)
    weather = await service.web.read_weather()
    assert weather["today"]["temperature"] == 12.0
    assert weather["forecasts"][0]["date"] == "2026-11-10"

    flow = await service.web.read_energyflow()
    assert flow["grid_power"] == -1200.0  # feed-in
    assert flow["pv_power"] == 2400.0
    assert flow["house_power"] is None  # removed in newer firmware


async def test_web_save_heatingcircuit_parameter_gated(fake: FakeTransport):
    service, _ = make_service(fake, web_pin="1234", allow_writes=True, write_classes="volatile")
    await service.ensure_ready()
    client = attach_fake_web(service)
    with pytest.raises(PermissionError, match="eeprom"):
        await service.web.save_heatingcircuit_parameter("HKA04", 22.0)

    service.settings.write_classes = {"eeprom"}
    result = await service.web.save_heatingcircuit_parameter(
        "HKA04", 22.0, min_value=5.0, max_value=28.0
    )
    assert result["parameter_id"] == "HKA04"
    assert (
        "save_heatingcircuit_parameter",
        ("HKA04", 22.0),
        {"min_value": 5.0, "max_value": 28.0},
    ) in client.calls

    with pytest.raises(ValueError, match="parameter_id"):
        await service.web.save_heatingcircuit_parameter("  ", 22.0)
