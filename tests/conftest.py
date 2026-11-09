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


class FakeWebClient:
    """Duck-typed Navigator 10 web client recording every call."""

    def __init__(self) -> None:
        from idm_heatpump.web import (
            IdmWebData,
            IdmWebDiagnostics,
            IdmWebNotification,
            IdmWebNotifications,
            IdmWebValue,
        )

        self._IdmWebData = IdmWebData
        self._IdmWebDiagnostics = IdmWebDiagnostics
        self._IdmWebNotifications = IdmWebNotifications
        self._IdmWebNotification = IdmWebNotification
        self._IdmWebValue = IdmWebValue
        self.calls: list[tuple[str, tuple, dict]] = []
        self.closed = False

    def _record(self, name: str, *args: object, **kwargs: object) -> None:
        self.calls.append((name, args, kwargs))

    async def read_data(self, **_: object) -> object:
        self._record("read_data")
        return self._IdmWebData(
            model="Navigator 10 Web",
            values={
                "software_version": self._IdmWebValue(
                    "software_version", "NAV10_20.24", "software_version"
                ),
                "heatpump_model": self._IdmWebValue(
                    "heatpump_model", "Terra MMW 406", "heatpump_model"
                ),
            },
        )

    async def read_notifications(self, **_: object) -> object:
        self._record("read_notifications")
        return self._IdmWebNotifications(
            current=(
                self._IdmWebNotification(
                    code="142",
                    message="Wärmepumpenvorlauf Maximaltemperatur",
                    severity="error",
                    deferrable=False,
                ),
            )
        )

    async def set_system_mode(self, mode: int) -> None:
        self._record("set_system_mode", int(mode))

    async def save_dhw_setpoint(self, celsius: float) -> None:
        self._record("save_dhw_setpoint", float(celsius))

    async def acknowledge_all_notifications(self) -> None:
        self._record("acknowledge_all_notifications")

    async def acknowledge_notification(self, code: str, *, remind_me_later: bool = False) -> None:
        self._record("acknowledge_notification", code, remind_me_later=remind_me_later)

    async def set_datetime(self, value: object) -> None:
        self._record("set_datetime", value)

    async def read_heatingcircuit(self, hc_id: str) -> object:
        from idm_heatpump.web import (
            IdmWebHeatingCircuit,
            IdmWebHeatingCircuitChoice,
            IdmWebHeatingCircuitRef,
            IdmWebHeatingCircuitValue,
        )

        self._record("read_heatingcircuit", hc_id)
        return IdmWebHeatingCircuit(
            hc_id=hc_id.upper(),
            display_name="Heizkreis A",
            mode_value=1,
            mode_parameter_id="HKA00",
            mode_options=(
                IdmWebHeatingCircuitChoice(key=0, name="Aus"),
                IdmWebHeatingCircuitChoice(key=1, name="Automatik"),
            ),
            setpoint_normal=IdmWebHeatingCircuitValue(
                parameter_id="HKA04", value=21.0, min_value=5.0, max_value=28.0
            ),
            setpoint_eco=IdmWebHeatingCircuitValue(
                parameter_id="HKA05", value=17.0, min_value=5.0, max_value=28.0
            ),
            room_temperature=21.4,
            flow_setpoint=34.0,
            pump_active=True,
            available_circuits=(IdmWebHeatingCircuitRef(hc_id="A"),),
        )

    async def read_weather(self) -> object:
        from idm_heatpump.web import IdmWebWeatherDay, IdmWebWeatherDetail

        self._record("read_weather")
        return IdmWebWeatherDetail(
            today=IdmWebWeatherDay(date="2026-11-09", temperature=12.0, temperature_min=7.0),
            forecasts=(IdmWebWeatherDay(date="2026-11-10", temperature=9.0),),
        )

    async def read_energyflow(self) -> object:
        from idm_heatpump.web import IdmWebEnergyflow

        self._record("read_energyflow")
        return IdmWebEnergyflow(grid_power=-1200.0, pv_power=2400.0, house_power=None)

    async def save_heatingcircuit_parameter(
        self,
        parameter_id: str,
        value: float,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> None:
        self._record(
            "save_heatingcircuit_parameter",
            parameter_id,
            value,
            min_value=min_value,
            max_value=max_value,
        )

    async def close(self) -> None:
        self.closed = True

    def get_cached_data(self) -> object | None:
        return None

    def diagnostics(self) -> object:
        return self._IdmWebDiagnostics(
            navigator_type="nav10", websocket_connected=True, web_data_enabled=True
        )


def attach_fake_web(
    service: IdmService, web_client: FakeWebClient | None = None, variant: str = "nav10"
) -> FakeWebClient:
    """Give a ready service a web supplement backed by a fake client."""
    from idm_mcp.web import WebSupplement

    web_client = web_client or FakeWebClient()
    service.web = WebSupplement(
        service.settings,
        "Navigator 10",
        gate=service._gate_web_write,
        client_factory=lambda: web_client,
    )
    service.settings.web_pin = service.settings.web_pin or "1234"
    service.settings.web_variant = variant
    return web_client


@pytest.fixture
def fake() -> FakeTransport:
    transport = FakeTransport()
    seed_navigator20_circuit_a(transport)
    return transport
