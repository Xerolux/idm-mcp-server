"""Test doubles and fixtures for the IDM MCP server.

The fake transport implements the ``IdmModbusTransport`` protocol in-memory.
Unlike a real device it rejects *unseeded* addresses with Illegal Data
Address, which keeps model detection and batch reads fast and deterministic.
"""

from __future__ import annotations

import struct

import pytest
from idm_heatpump import IdmModbusClient
from idm_heatpump.client import IllegalAddressError

from idm_mcp.config import Settings
from idm_mcp.service import IdmService


class FakeTransport:
    """Minimal async transport double; seeded addresses answer, others reject."""

    def __init__(self) -> None:
        self.input_registers: dict[int, int] = {}
        self.holding_registers: dict[int, int] = {}
        self.read_calls: list[tuple[str, int, int]] = []
        self.write_calls: list[tuple[int, list[int]]] = []
        self.connected = False

    async def connect(self) -> None:
        self.connected = True

    async def close(self) -> None:
        self.connected = False

    async def read_input_registers(self, *, address: int, count: int) -> list[int]:
        return self._read("input", self.input_registers, address, count)

    async def read_holding_registers(self, *, address: int, count: int) -> list[int]:
        return self._read("holding", self.holding_registers, address, count)

    async def write_registers(self, *, address: int, values: list[int]) -> None:
        self.write_calls.append((address, list(values)))
        for offset, value in enumerate(values):
            self.holding_registers[address + offset] = int(value)

    def _read(self, kind: str, store: dict[int, int], address: int, count: int) -> list[int]:
        self.read_calls.append((kind, address, count))
        missing = [address + offset for offset in range(count) if address + offset not in store]
        if missing:
            raise IllegalAddressError(f"Illegal Data Address reading {kind} register {missing[0]}")
        return [store[address + offset] for offset in range(count)]

    # seeding helpers ---------------------------------------------------

    def seed_float(self, address: int, value: float, *, store: str = "input") -> None:
        low, high = struct.unpack("<HH", struct.pack("<f", value))
        target = self.input_registers if store == "input" else self.holding_registers
        target[address] = low
        target[address + 1] = high

    def seed_word(self, address: int, value: int, *, store: str = "input") -> None:
        target = self.input_registers if store == "input" else self.holding_registers
        target[address] = value & 0xFFFF


def seed_navigator20_circuit_a(fake: FakeTransport) -> None:
    """Seed a Navigator 2.0 plant with heating circuit A active."""
    fake.seed_float(1000, 12.5)  # outdoor_temp
    fake.seed_float(1002, 12.1)  # outdoor_temp_avg
    fake.seed_word(1004, 0)  # internal_message: no error
    fake.seed_word(1005, 1)  # system_mode
    fake.seed_float(1008, 48.5)  # storage_temp
    fake.seed_float(1010, -1.0)  # cold_storage_temp: unused sentinel
    fake.seed_float(1012, 46.0)  # dhw_temp_bottom
    fake.seed_float(1014, 55.0)  # dhw_temp_top
    fake.seed_word(1032, 48)  # dhw_setpoint
    fake.seed_float(1350, 34.2)  # hc_a_flow_temp
    for slot in range(1, 7):  # circuits B-G: unconfigured sentinels
        fake.seed_float(1350 + slot * 2, -1.0)
    fake.seed_word(1498, 3)  # hc_a active mode
    for slot in range(1, 7):
        fake.seed_word(1498 + slot, 0xFFFF)
    # Everything else (PV 74, cascade 1147, solar 1850, ISC 1870, zones 2000,
    # Navigator-10 block 4001+) stays unseeded and rejects with Illegal Data
    # Address, so detection classifies the plant as Navigator 2.0, circuit A.


def make_service(fake: FakeTransport, **settings_overrides) -> tuple[IdmService, FakeTransport]:
    values = {"host": "heatpump.local"} | settings_overrides
    settings = Settings(**values)
    client = IdmModbusClient(
        host=settings.host or "unconfigured",
        port=settings.port,
        slave_id=settings.slave_id,
        timeout=settings.timeout,
        max_retries=settings.max_retries,
        transport=fake,
    )
    return IdmService(settings, client), fake


@pytest.fixture
def fake() -> FakeTransport:
    transport = FakeTransport()
    seed_navigator20_circuit_a(transport)
    return transport
