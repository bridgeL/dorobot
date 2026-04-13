"""DoroBot 核心类"""

import asyncio
from typing import Optional
from loguru import logger


class Dorobot:
    """DoroBot 核心类

    提供标准化的生命周期管理：
    - init()      - 初始化（仅初始化，不启动）
    - run_forever() - 永久阻塞运行，Ctrl+C 可结束
    - start()     - 后台运行，可用 stop() 停止
    - stop()      - 停止
    """

    _instance: Optional["Dorobot"] = None

    def __init__(self):
        self._running = False

        # 创建所有管理器实例
        from .bot_manager import BotManager
        from .session_manager import SessionManager
        from .space_manager import SpaceManager
        from .adapter_manager import AdapterManager
        from .router import MessageRouter

        self.bot_manager = BotManager(self)
        self.session_manager = SessionManager(self)
        self.space_manager = SpaceManager(self)
        self.adapter_manager = AdapterManager(self)
        self.router = MessageRouter(self)

    @classmethod
    def get_instance(cls) -> "Dorobot":
        if cls._instance is None:
            cls._instance = Dorobot()
        return cls._instance

    def init(self):
        """初始化 DoroBot：配置日志、加载插件、初始化 Space"""
        from .utils import init_logging
        from . import context as ctx

        init_logging(level="DEBUG")
        ctx.set_dorobot(self)
        self.space_manager.init()
        logger.info("DoroBot initialized")

    def run_forever(self):
        """阻塞运行，永久保持直到 Ctrl+C"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # 没有运行中的循环，创建新的
            asyncio.run(self._run_blocking())
        else:
            # 已有循环在此线程中运行（如 Jupyter/Claude Code），使用 run_until_complete
            loop.run_until_complete(self._run_blocking())

    def start(self):
        """后台启动，不阻塞，可通过 stop() 停止"""
        if self._running:
            logger.warning("DoroBot is already running")
            return

        async def _start_bg():
            await self._run()

        asyncio.create_task(_start_bg())
        self._running = True
        logger.info("DoroBot started in background")

    async def stop(self):
        """停止 DoroBot"""
        if not self._running:
            return

        self._running = False
        await self.adapter_manager.stop_all()
        self.space_manager.stop()
        logger.info("DoroBot stopped")

    async def _run(self):
        """内部运行协程"""
        await self.adapter_manager.start_all()
        self.space_manager.start()
        self._running = True

        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            self.space_manager.stop()
            logger.info("DoroBot stopped")

    async def _run_blocking(self):
        """阻塞运行，直到收到 KeyboardInterrupt"""
        logger.info("=" * 50)
        logger.info("DoroBot Starting...")
        logger.info("=" * 50)

        await self.adapter_manager.start_all()
        self.space_manager.start()

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.space_manager.stop()
            logger.info("DoroBot stopped")

    def add_adapter(self, adapter: "Adapter") -> bool:  # type: ignore[name-defined]
        """注册适配器到 Dorobot

        Args:
            adapter: 适配器实例

        Returns:
            bool: 是否注册成功
        """
        return self.adapter_manager.register(adapter)

    def load_plugins(self):
        """加载插件"""
        from .utils import load_plugins

        load_plugins()
