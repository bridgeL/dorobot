"""Bot 管理器

统一管理所有 Bot 实例的注册、初始化和生命周期。
采用单例模式，全局只有一个 BotManager 实例。
"""
from typing import Optional, Type, Callable, Awaitable
import asyncio
from loguru import logger

from .bot import Bot


class BotManager:
    """Bot 管理器（单例）

    管理所有 Bot 实例：
    - 注册 Bot 类
    - 自动创建和初始化 Bot 实例
    - 统一管理所有 Bot 的启动和停止
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._bot_classes: dict[str, Type[Bot]] = {}  # name -> BotClass
        self._bot_instances: dict[str, Bot] = {}      # name -> BotInstance
        self._bot_metadata: dict[str, dict] = {}      # name -> {auto_start, ...}
        self._pending_starts: list[str] = []          # bots waiting to be started
        self._initialized = True

    def register(self, name: str, bot_class: Type[Bot], auto_start: bool = True, **metadata) -> bool:
        """注册 Bot 类

        Args:
            name: Bot 唯一名称
            bot_class: Bot 类（必须继承 Bot）
            auto_start: 是否自动启动
            **metadata: 其他元数据，会传递给 Bot 构造函数

        Returns:
            bool: 是否注册成功
        """
        if name in self._bot_classes:
            logger.warning(f"Bot {name} already registered")
            return False

        if not issubclass(bot_class, Bot):
            logger.error(f"Bot class must inherit from Bot")
            return False

        self._bot_classes[name] = bot_class
        self._bot_metadata[name] = {
            "auto_start": auto_start,
            **metadata
        }

        # 自动创建实例
        try:
            instance = bot_class(**metadata)
            self._bot_instances[name] = instance
            logger.success(f"Registered and created bot: {name}")

            # 自动启动（如果有事件循环）
            if auto_start:
                try:
                    loop = asyncio.get_running_loop()
                    asyncio.create_task(self._start_bot(name))
                except RuntimeError:
                    # 没有运行的事件循环，添加到待启动列表
                    self._pending_starts.append(name)

            return True
        except Exception as e:
            logger.error(f"Failed to create bot {name}: {e}")
            return False

    async def _start_bot(self, name: str):
        """启动指定 Bot"""
        instance = self._bot_instances.get(name)
        if not instance:
            return

        try:
            logger.info(f"Starting bot: {name}")
            await instance.start()
        except Exception as e:
            logger.error(f"Bot {name} failed to start: {e}")

    def get_bot(self, name: str) -> Optional[Bot]:
        """获取 Bot 实例"""
        return self._bot_instances.get(name)

    def get_all_bots(self) -> dict[str, Bot]:
        """获取所有 Bot 实例"""
        return self._bot_instances.copy()

    def list_bots(self) -> list[str]:
        """列出所有已注册的 Bot 名称"""
        return list(self._bot_instances.keys())

    async def stop_all(self):
        """停止所有 Bot"""
        logger.info("Stopping all bots...")
        tasks = []
        for name, bot in self._bot_instances.items():
            logger.debug(f"Stopping bot: {name}")
            tasks.append(self._stop_bot_safe(name, bot))

        await asyncio.gather(*tasks, return_exceptions=True)
        self._bot_instances.clear()
        logger.success("All bots stopped")

    async def _stop_bot_safe(self, name: str, bot: Bot):
        """安全停止单个 Bot"""
        try:
            await bot.stop()
        except Exception as e:
            logger.error(f"Error stopping bot {name}: {e}")

    async def stop_bot(self, name: str) -> bool:
        """停止指定 Bot"""
        bot = self._bot_instances.get(name)
        if not bot:
            return False

        try:
            await bot.stop()
            del self._bot_instances[name]
            logger.info(f"Stopped bot: {name}")
            return True
        except Exception as e:
            logger.error(f"Error stopping bot {name}: {e}")
            return False

    async def start_all(self):
        """启动所有待启动的 bot"""
        if not self._pending_starts:
            return

        logger.info(f"Starting {len(self._pending_starts)} pending bots...")
        tasks = []
        for name in self._pending_starts:
            tasks.append(self._start_bot(name))

        await asyncio.gather(*tasks, return_exceptions=True)
        self._pending_starts.clear()

    def clear(self):
        """清空所有注册信息（危险操作）"""
        self._bot_classes.clear()
        self._bot_instances.clear()
        self._bot_metadata.clear()
        logger.warning("BotManager cleared all registrations")


# 全局 BotManager 实例
bot_manager = BotManager()


def register_bot(name: str, auto_start: bool = True, **kwargs):
    """装饰器：注册 Bot 类

    使用示例：
        @register_bot("console", auto_start=True, sender_name="User")
        class ConsoleBot(Bot):
            async def send(self, session_id, content):
                print(f"[Bot] {content}")

        # 在其他地方获取 Bot 实例
        console = bot_manager.get_bot("console")
    """
    def decorator(cls):
        bot_manager.register(name, cls, auto_start=auto_start, **kwargs)
        return cls
    return decorator
