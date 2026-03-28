"""消息路由系统

连接Bot和插件系统，负责消息的分发和路由。
协调 BotManager 和 SessionManager 的关系。
"""
import asyncio
from loguru import logger

from dorobot.plugin import Message
from dorobot.session_manager import session_manager
from dorobot.bot_manager import bot_manager
from dorobot.bot import Bot
import dorobot.context as ctx


class MessageRouter:
    """消息路由器

    核心职责：
    1. 协调 BotManager 管理 Bot 生命周期
    2. 协调 SessionManager 管理会话生命周期
    3. 接收 Bot 消息并路由到对应会话的插件
    4. 处理跨 Bot/会话的消息发送

    会话分层结构：
       - 0层（meta层）：只有 meta plugin，无法关闭
       - 1层（命令层）：共享层，可激活多个插件
       - 2层（应用层）：独占层，只能激活1个插件
       - 3层（共享层）：共享层，可激活多个插件
    """

    def __init__(self):
        """初始化消息路由器"""
        self._session_manager = session_manager
        self._bot_tasks: dict[str, asyncio.Task] = {}  # bot_id -> running task
        logger.info("MessageRouter initialized")

    async def _run_bot(self, bot_id: str, bot: Bot):
        """运行 Bot 并处理异常"""
        try:
            await bot.start()
        except Exception as e:
            logger.error(f"Bot {bot_id} crashed: {e}")
        finally:
            bot_manager.remove_bot(bot_id)
            self._bot_tasks.pop(bot_id, None)

    async def start_all(self):
        """启动所有已注册的 Bot"""
        for bot_id, bot in bot_manager.get_all_bots().items():
            if bot_id not in self._bot_tasks:
                task = asyncio.create_task(self._run_bot(bot_id, bot))
                self._bot_tasks[bot_id] = task
                logger.info(f"Started bot: {bot_id}")

    async def stop_bot(self, bot_id: str):
        """停止指定 Bot"""
        bot = bot_manager.get_bot(bot_id)
        if not bot:
            return

        await bot.stop()

        # 取消任务
        task = self._bot_tasks.get(bot_id)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        bot_manager.remove_bot(bot_id)
        self._bot_tasks.pop(bot_id, None)
        logger.info(f"Stopped bot: {bot_id}")

    async def stop_all(self):
        """停止所有 Bot"""
        tasks = [self.stop_bot(bot_id) for bot_id in bot_manager.list_bots()]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def handle_message(self, bot_id: str, session_id: str, message_data: dict) -> bool:
        """处理 Bot 发来的消息

        这是 Bot 收到消息后应该调用的入口方法。

        Args:
            bot_id: Bot 的唯一标识
            session_id: 会话ID
            message_data: 原始消息数据，包含 content, sender_id, sender_name, msg_type 等

        Returns:
            bool: 消息是否被完全处理
        """
        # 通过 SessionManager 获取或创建会话
        session = await self._session_manager.get_or_create_session(session_id)

        # 设置上下文变量
        ctx.bot_id.set(bot_id)
        ctx.session_id.set(session_id)

        try:
            # 构造消息对象
            message = Message(
                content=message_data.get("content", ""),
                sender_id=message_data.get("sender_id", ""),
                sender_name=message_data.get("sender_name", ""),
                msg_type=message_data.get("msg_type", "text"),
                raw_data=message_data
            )

            content_preview = message.content[:50] + "..." if len(message.content) > 50 else message.content
            logger.info(f"[Router] Routing message: bot={bot_id}, session={session_id}, sender={message.sender_name}, content='{content_preview}'")
            result = await session.handle_message(message)
            return result
        finally:
            # 清理上下文（可选，因为contextvars会自动处理）
            pass

    def send_message(self, session_id: str, content: str, bot_id: str | None = None) -> None:
        """发送消息到指定会话

        如果 bot_id 未指定，从上下文获取

        Args:
            session_id: 会话ID
            content: 消息内容
            bot_id: Bot 的唯一标识，None 则从上下文获取
        """
        if bot_id is None:
            bot_id = ctx.get_bot_id()

        bot = bot_manager.get_bot(bot_id) if bot_id else None
        if not bot:
            logger.error("No bot available to send message")
            return

        asyncio.create_task(bot.send(session_id, content))

    def __repr__(self):
        return f"MessageRouter(bots={bot_manager.list_bots()}, session_manager={self._session_manager})"


# 全局 MessageRouter 实例
router = MessageRouter()
