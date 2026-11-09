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


async def test_bearer_auth_middleware_rejects_and_accepts():
    from idm_mcp.server import BearerAuthMiddleware

    class Recorder:
        def __init__(self) -> None:
            self.calls: list[str] = []

        async def __call__(self, scope, receive, send):
            self.calls.append(scope["type"])

    inner = Recorder()
    middleware = BearerAuthMiddleware(inner, "secret-token")

    async def call_http(auth_header: bytes | None) -> tuple[int, list[dict]]:
        headers = [] if auth_header is None else [(b"authorization", auth_header)]
        responses: list[dict] = []

        async def receive():  # pragma: no cover - unused
            return {}

        async def send(message):
            responses.append(message)

        await middleware({"type": "http", "headers": headers}, receive, send)
        status = next((m["status"] for m in responses if m["type"] == "http.response.start"), 200)
        return status, responses

    status, _ = await call_http(None)
    assert status == 401
    status, _ = await call_http(b"Bearer wrong")
    assert status == 401
    status, _ = await call_http(b"Bearer secret-token")
    assert status == 200
    assert inner.calls == ["http"]

    # Non-HTTP scopes (lifespan) pass through untouched.
    await middleware({"type": "lifespan", "headers": []}, None, None)
    assert inner.calls == ["http", "lifespan"]


def test_http_token_setting_parsed(monkeypatch):
    assert Settings(host="hp", _env_file=None).http_token == ""
    monkeypatch.setenv("IDM_HTTP_TOKEN", "abc123")
    assert Settings(host="hp", _env_file=None).http_token == "abc123"
