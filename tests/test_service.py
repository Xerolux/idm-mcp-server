"""Service-layer tests against the in-memory fake transport."""

from __future__ import annotations

import pytest
from conftest import make_service


async def test_detect_model_navigator20_with_circuit_a(fake):
    service, _ = make_service(fake)
    model = await service.detect_model()
    assert model["model_name"] == "Navigator 2.0"
    assert model["active_heating_circuits"] == ["A"]
    assert model["detected"] is True
    assert model["zone_modules"] == 0
    assert model["has_solar"] is False


async def test_manual_model_override_skips_detection(fake):
    service, _ = make_service(fake, model="navigator10", heating_circuits="a,b")
    model = await service.detect_model()
    assert model["model_name"] == "Navigator 10"
    assert model["active_heating_circuits"] == ["A", "B"]
    assert model["detected"] is False


async def test_list_datapoints_contains_core_registers(fake):
    service, _ = make_service(fake)
    await service.detect_model()
    items = service.list_datapoints()
    keys = {item["key"] for item in items}
    assert {"outdoor_temp", "storage_temp", "dhw_setpoint", "hc_a_flow_temp"} <= keys
    dhw = next(item for item in items if item["key"] == "dhw_setpoint")
    assert dhw["writable"] is True
    assert dhw["write_class"] == "eeprom"
    assert dhw["min"] == 35
    assert dhw["max"] == 95

    writable = service.list_datapoints(writable_only=True)
    assert writable
    assert all(item["writable"] for item in writable)

    dhw_only = service.list_datapoints(category="dhw")
    assert dhw_only
    assert all("dhw" in item["key"] for item in dhw_only)


async def test_read_datapoint_decodes_float_and_unit(fake):
    service, _ = make_service(fake)
    result = await service.read_datapoint("outdoor_temp")
    assert result["value"] == pytest.approx(12.5)
    assert result["unit"] == "°C"


async def test_read_datapoint_maps_enum_label(fake):
    service, _ = make_service(fake)
    fake.seed_word(1005, 1)  # system_mode = 1
    result = await service.read_datapoint("system_mode")
    assert result["value"] == 1
    assert result["enum_label"]
    assert result["enum_options"][1] == result["enum_label"]


async def test_read_datapoint_marks_sentinel_as_unused(fake):
    service, _ = make_service(fake)
    result = await service.read_datapoint("cold_storage_temp")
    assert result["unused"] is True


async def test_read_datapoint_rejects_unknown_and_write_only(fake):
    service, _ = make_service(fake)
    with pytest.raises(KeyError, match="unknown datapoint"):
        await service.read_datapoint("does_not_exist")
    with pytest.raises(ValueError, match="write-only"):
        await service.read_datapoint("error_acknowledge")


async def test_read_all_returns_batch_snapshot(fake):
    service, _ = make_service(fake)
    snapshot = await service.read_all()
    assert snapshot["model"]["model_name"] == "Navigator 2.0"
    assert snapshot["values"]["outdoor_temp"]["value"] == pytest.approx(12.5)
    assert snapshot["values"]["storage_temp"]["unit"] == "°C"
    assert snapshot["value_count"] >= 4
    # unseeded registers reject and must be counted, not crash the snapshot
    assert snapshot["failed_count"] > 0

    cached = await service.read_all()
    assert cached["cached"] is True
    refreshed = await service.read_all(refresh=True)
    assert refreshed["cached"] is False


async def test_validate_write_plans_without_device_write(fake):
    service, _ = make_service(fake)
    plan = await service.validate_write("dhw_setpoint", 52)
    assert plan["dry_run"] is True
    assert plan["write_class"] == "eeprom"
    assert plan["encoded_registers"] == [52]
    assert fake.write_calls == []
    with pytest.raises(ValueError, match="exceeds maximum"):
        await service.validate_write("dhw_setpoint", 120)  # above max 95


async def test_write_disabled_by_default(fake):
    service, _ = make_service(fake)
    with pytest.raises(PermissionError, match="writes are disabled"):
        await service.write_datapoint("dhw_setpoint", 52)


async def test_write_requires_write_class_allowlist(fake):
    service, _ = make_service(fake, allow_writes=True, write_classes="volatile")
    with pytest.raises(PermissionError, match="write class 'eeprom'"):
        await service.write_datapoint("dhw_setpoint", 52)


async def test_write_requires_key_allowlist(fake):
    service, _ = make_service(
        fake,
        allow_writes=True,
        write_classes="eeprom",
        writable_keys="system_mode",
    )
    with pytest.raises(PermissionError, match="IDM_WRITABLE_KEYS"):
        await service.write_datapoint("dhw_setpoint", 52)


async def test_write_rejects_read_only_datapoint(fake):
    service, _ = make_service(fake, allow_writes=True, write_classes="eeprom")
    with pytest.raises(PermissionError, match="read-only"):
        await service.write_datapoint("outdoor_temp", 20)


async def test_successful_write_encodes_and_forwards(fake):
    service, _ = make_service(fake, allow_writes=True, write_classes="eeprom")
    result = await service.write_datapoint("dhw_setpoint", 52)
    assert result["value"] == 52
    assert result["dry_run"] is False
    assert result["encoded_registers"] == [52]
    assert fake.write_calls == [(1032, [52])]
    with pytest.raises(ValueError, match="too recently"):
        # API EEPROM throttle refuses a second write to the same register
        await service.write_datapoint("dhw_setpoint", 53)


async def test_write_dry_run_never_reaches_device(fake):
    service, _ = make_service(fake, allow_writes=False)
    plan = await service.write_datapoint("dhw_setpoint", 52, dry_run=True)
    assert plan["dry_run"] is True
    assert fake.write_calls == []


async def test_explain_error_code(fake):
    service, _ = make_service(fake)
    known = service.explain_error_code(0)
    assert known["known"] is True
    unknown = service.explain_error_code(99999)
    assert unknown["known"] is False


async def test_diagnostics_reports_model_and_health(fake):
    service, _ = make_service(fake)
    diag = await service.diagnostics()
    assert diag["host"] == "heatpump.local"
    assert diag["model"]["model_name"] == "Navigator 2.0"
    assert diag["datapoint_count"] > 50
    assert "unsupported_registers" in diag


async def test_missing_host_is_actionable(fake):
    service, _ = make_service(fake, host="")
    with pytest.raises(RuntimeError, match="IDM_HOST"):
        await service.ensure_ready()
