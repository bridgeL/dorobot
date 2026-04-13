import asyncio
from loguru import logger
from .adapter import Adapter


class AdapterManager:
    def __init__(self, dorobot: "Dorobot"):
        self._dorobot = dorobot
        self._adapters: dict[str, Adapter] = {}

    def register(self, adapter: Adapter) -> bool:
        name = adapter.name
        if name in self._adapters:
            logger.warning(f"Adapter {name} already registered")
            return False

        adapter.bind_dorobot(self._dorobot)

        self._adapters[name] = adapter
        logger.info(f"Registered Adapter: {name}")

        return True

    async def start_all(self):
        tasks = []
        for name, adapter in self._adapters.items():
            tasks.append(self._start_adapter_safe(name, adapter))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_all(self):
        """停止所有适配器"""
        tasks = []
        for name, adapter in self._adapters.items():
            tasks.append(self._stop_adapter_safe(name, adapter))
        await asyncio.gather(*tasks, return_exceptions=True)
        self._adapters.clear()

    async def _start_adapter_safe(self, name: str, adapter: Adapter):
        try:
            await adapter.start()
        except Exception as e:
            logger.error(f"Adapter {name} failed to start: {e}")

    async def _stop_adapter_safe(self, name: str, adapter: Adapter):
        try:
            await adapter.stop()
            logger.info(f"Adapter {name} stopped")
        except Exception as e:
            logger.error(f"Adapter {name} failed to stop: {e}")