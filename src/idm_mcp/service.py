class IdmService:
    def __init__(self, settings, registry, client):
        self.settings, self.registry, self.client = settings, registry, client

    def list_entities(self):
        return [entity.model_dump() for entity in self.registry.entities.values()]

    def entity(self, name):
        if name not in self.registry.entities:
            raise KeyError(f"unknown entity {name!r}")
        return self.registry.entities[name]

    async def read_entity(self, name):
        entity = self.entity(name)
        raw = await self.client.read(entity.address, entity.register_type)
        return {"name": name, "value": entity.decode(raw), "unit": entity.unit, "raw": raw}

    async def write_entity(self, name, value):
        entity = self.entity(name)
        if not self.settings.allow_writes:
            raise PermissionError("writes are disabled")
        if not entity.writable:
            raise PermissionError(f"entity {name!r} is read-only")
        if entity.address not in self.settings.writable_addresses:
            raise PermissionError(f"address {entity.address} is not in write allowlist")
        raw = entity.encode(value)
        await self.client.write(entity.address, raw)
        return {"name": name, "value": value, "unit": entity.unit, "raw": raw}
