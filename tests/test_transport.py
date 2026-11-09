"""Transport selection and HTTP settings tests."""

from __future__ import annotations

import pytest

from idm_mcp.config import Settings
from idm_mcp.server import _apply_http_settings, mcp


def test_transport_defaults_to_stdio(monkeypatch):
    monkeypatch.delenv("IDM_TRANSPORT", raising=False)
    settings = Settings(host="hp", _env_file=None)
    assert settings.transport == "stdio"
    assert settings.http_host == "127.0.0.1"
    assert settings.http_port == 8308


def test_transport_env_parsed(monkeypatch):
    monkeypatch.setenv("IDM_TRANSPORT", "http")
    monkeypatch.setenv("IDM_HTTP_HOST", "0.0.0.0")
    monkeypatch.setenv("IDM_HTTP_PORT", "9000")
    settings = Settings(host="hp", _env_file=None)
    assert settings.transport == "http"
    assert settings.http_host == "0.0.0.0"
    assert settings.http_port == 9000
    with pytest.raises(ValueError):
        Settings(host="hp", transport="grpc", _env_file=None)


def test_web_variant_validation():
    for value in ("auto", "nav10", "nav20", "off", ""):
        assert Settings(host="hp", web_variant=value).web_variant == value or value == ""
    with pytest.raises(ValueError, match="web_variant"):
        Settings(host="hp", web_variant="nav12")


def test_apply_http_settings_binds_configured_address():
    original = (mcp.settings.host, mcp.settings.port)
    try:
        settings = Settings(host="hp", http_host="192.168.0.5", http_port=9999, _env_file=None)
        _apply_http_settings(mcp, settings)
        assert mcp.settings.host == "192.168.0.5"
        assert mcp.settings.port == 9999
    finally:
        mcp.settings.host, mcp.settings.port = original
