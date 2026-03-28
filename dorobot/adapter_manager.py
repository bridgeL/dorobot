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

adapter_manager = AdapterManager()