from pymodbus.client import AsyncModbusTcpClient


class IdmClient:
    def __init__(self, settings, client=None):
        self.settings = settings
        self.client = client or AsyncModbusTcpClient(
            settings.host, port=settings.port, timeout=settings.timeout
        )

    async def connect(self):
        if not self.settings.host:
            raise RuntimeError("IDM_HOST is not configured")
        if not self.client.connected and not await self.client.connect():
            raise ConnectionError(f"cannot connect to IDM heat pump at {self.settings.host}")

    async def read(self, address, register_type="holding"):
        await self.connect()
        method = (self.client.read_input_registers if register_type == "input"
                  else self.client.read_holding_registers)
        result = await method(address=address, count=1, slave=self.settings.unit_id)
        if result.isError():
            raise RuntimeError(f"Modbus read failed: {result}")
        return int(result.registers[0])

    async def write(self, address, value):
        await self.connect()
        result = await self.client.write_register(
            address=address, value=value, slave=self.settings.unit_id
        )
        if result.isError():
            raise RuntimeError(f"Modbus write failed: {result}")
