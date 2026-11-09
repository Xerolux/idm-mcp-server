"""Smoke tests for the FastMCP tool and resource wiring."""

from __future__ import annotations

import json

import pytest
from conftest import FakeTransport, make_service
from mcp.server.fastmcp.exceptions import ToolError

import idm_mcp.server as server_module


@pytest.fixture
def patched_service(fake: FakeTransport, monkeypatch):
    service, _ = make_service(fake, allow_writes=True, write_classes="eeprom")
    monkeypatch.setattr(server_module, "_service", service)
    return service


def _tool_names() -> set[str]:
    return {tool.name for tool in server_module.mcp._tool_manager.list_tools()}


def test_expected_tools_are_registered():
    assert {
        "detect_model",
        "list_datapoints",
        "read_datapoint",
        "read_all_datapoints",
        "validate_write",
        "write_datapoint",
        "explain_error_code",
        "get_diagnostics",
    } <= _tool_names()


def test_expected_resources_are_registered():
    uris = {str(resource.uri) for resource in server_module.mcp._resource_manager.list_resources()}
    # template resources are registered separately
    templates = {
        template.uri_template for template in server_module.mcp._resource_manager.list_templates()
    }
    assert "idm://datapoints" in uris
    assert "idm://datapoints/{key}" in templates


async def test_read_datapoint_tool_roundtrip(patched_service):
    raw = await server_module.mcp.call_tool("read_datapoint", {"key": "outdoor_temp"})
    payload = json.loads(raw[0][0].text)
    assert payload["value"] == pytest.approx(12.5)


async def test_write_tool_respects_gates_locally(patched_service, monkeypatch):
    # Downgrade settings so the gate rejects despite the patched service.
    patched_service.settings.allow_writes = False
    with pytest.raises(ToolError, match="writes are disabled"):
        await server_module.mcp.call_tool("write_datapoint", {"key": "dhw_setpoint", "value": 52})
