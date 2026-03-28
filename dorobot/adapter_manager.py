import asyncio
from loguru import logger
from dorobot.adapter import Adapter


class AdapterManager:
    def __init__(self):
        self._adapters: dict[str, Adapter] = {}

    def register(self, adapter: Adapter) -> bool:
        name = adapter.name
        if name in self._adapters:
            logger.warning(f"Adapter {name} already registered")
            return False

        self._adapters[name] = adapter
        logger.info(f"Adapter {name} registered")

        return True

    async def start_all(self):
        tasks = []
        for name, adapter in self._adapters.items():
            tasks.append(self._start_adapter_safe(name, adapter))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _start_adapter_safe(self, name: str, adapter: Adapter):
        try:
            await adapter.start()
        except Exception as e:
            logger.error(f"Adapter {name} failed to start: {e}")


adapter_manager = AdapterManager()