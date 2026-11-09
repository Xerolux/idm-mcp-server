"""Settings parsing tests."""

from __future__ import annotations

import pytest

from idm_mcp.config import Settings, normalize_model_name


def test_defaults_are_read_only():
    settings = Settings(host="hp")
    assert settings.allow_writes is False
    assert settings.write_classes == frozenset()
    assert settings.cache_ttl == 5.0
    assert settings.model == ""


def test_write_classes_parse_csv_and_validate():
    settings = Settings(host="hp", write_classes="eeprom, volatile")
    assert settings.write_classes == {"eeprom", "volatile"}
    with pytest.raises(ValueError, match="invalid write classes"):
        Settings(host="hp", write_classes="eeprom, forbidden")


def test_writable_keys_parse_csv():
    settings = Settings(host="hp", writable_keys="dhw_setpoint, system_mode")
    assert settings.writable_keys == {"dhw_setpoint", "system_mode"}


def test_model_aliases_normalize():
    assert normalize_model_name("navigator10") == "Navigator 10"
    assert normalize_model_name(" Navigator 2.0 ") == "Navigator 2.0"
    assert normalize_model_name("navigatorpro") == "Navigator Pro"
    assert normalize_model_name("") == ""
    settings = Settings(host="hp", model="navigator10")
    assert settings.model == "Navigator 10"


def test_heating_circuits_normalize_and_validate():
    settings = Settings(host="hp", heating_circuits="a, b")
    assert settings.circuit_letters == ["A", "B"]
    with pytest.raises(ValueError, match="invalid heating circuit"):
        Settings(host="hp", heating_circuits="X")


def test_env_variables_are_read(monkeypatch):
    monkeypatch.setenv("IDM_HOST", "10.0.0.7")
    monkeypatch.setenv("IDM_ALLOW_WRITES", "true")
    monkeypatch.setenv("IDM_WRITE_CLASSES", "eeprom,cyclic")
    monkeypatch.setenv("IDM_WRITABLE_KEYS", "dhw_setpoint")
    monkeypatch.setenv("IDM_ZONE_MODULES", "2")
    settings = Settings(_env_file=None)
    assert settings.host == "10.0.0.7"
    assert settings.allow_writes is True
    assert settings.write_classes == {"eeprom", "cyclic"}
    assert settings.writable_keys == {"dhw_setpoint"}
    assert settings.zone_modules == 2
