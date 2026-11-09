"""Poller and cyclic-write maintenance tests."""

from __future__ import annotations

import asyncio

import pytest
from conftest import FakeTransport, make_service
from idm_heatpump import IdmConnectionError

import idm_mcp.server as server_module


async def test_poll_once_updates_state(fake: FakeTransport):
    service, _ = make_service(fake, poll_interval=30)
    snapshot = await service.poll_once()
    assert snapshot["cached"] is False
    state = service.poll_state
    assert state["poll_count"] == 1
    assert state["consecutive_failures"] == 0
    assert state["last_ok_at"] == state["last_poll_at"]
    assert state["last_error"] is None


async def test_poll_once_tracks_failures():
    class FailingTransport(FakeTransport):
        async def read_input_registers(self, *, address: int, count: int) -> list[int]:
            raise IdmConnectionError("plant unreachable")

        async def read_holding_registers(self, *, address: int, count: int) -> list[int]:
            raise IdmConnectionError("plant unreachable")

    failing = FailingTransport()
    service, _ = make_service(failing)
    with pytest.raises(IdmConnectionError):
        await service.poll_once()
    assert service.poll_state["consecutive_failures"] == 1
    assert "IdmConnectionError" in service.poll_state["last_error"]


async def test_cyclic_write_is_remembered_and_maintained(fake: FakeTransport):
    service, _ = make_service(fake, allow_writes=True, write_classes="cyclic")
    await service.ensure_ready()
    assert "glt_temp_demand_heating" in service._registers, "cyclic register must be in map"

    result = await service.write_datapoint("glt_temp_demand_heating", 35.0)
    assert result["write_class"] == "cyclic"
    assert service._cyclic_values == {"glt_temp_demand_heating": 35.0}
    first_write = list(fake.write_calls)

    # Far from the TTL deadline: nothing to do.
    assert await service.maintain_cyclic_writes() == 0
    assert fake.write_calls == first_write

    # Nearing (or past) the deadline: the demand is rewritten.
    assert await service.maintain_cyclic_writes(margin=301.0) == 1
    assert fake.write_calls == first_write + [(1696, list(fake.write_calls[-1][1]))]
    assert fake.write_calls[-1] == first_write[-1]


async def test_maintain_cyclic_writes_ignores_unknown_keys(fake: FakeTransport):
    service, _ = make_service(fake, allow_writes=True, write_classes="cyclic")
    await service.ensure_ready()
    service._cyclic_values = {"not_in_map": 1.0}
    assert await service.maintain_cyclic_writes(margin=10_000.0) == 0


async def test_poll_loop_runs_and_stops(fake: FakeTransport, monkeypatch):
    service, _ = make_service(fake, poll_interval=0.05)
    monkeypatch.setattr(server_module, "_service", service)
    task = asyncio.create_task(server_module._poll_loop(0.05))
    await asyncio.sleep(0.25)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    state = service.poll_state
    assert state["enabled"] is True
    assert state["poll_count"] >= 2
    assert state["interval"] == 0.05


async def test_app_lifespan_starts_and_stops_poller(fake: FakeTransport, monkeypatch):
    service, _ = make_service(fake, poll_interval=0.05)
    monkeypatch.setattr(server_module, "_service", service)
    async with server_module.app_lifespan(server_module.mcp):
        await asyncio.sleep(0.15)
        assert service.poll_state["enabled"] is True
        assert service.poll_state["poll_count"] >= 1
    assert service.poll_state["enabled"] is False


async def test_app_lifespan_without_polling(fake: FakeTransport, monkeypatch):
    service, _ = make_service(fake, poll_interval=0)
    monkeypatch.setattr(server_module, "_service", service)
    async with server_module.app_lifespan(server_module.mcp):
        await asyncio.sleep(0.02)
    assert service.poll_state["enabled"] is False
