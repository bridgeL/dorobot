"""消息路由系统

连接Bot和插件系统，负责消息的分发和路由。
协调 BotManager 和 SessionManager 的关系。
"""
import asyncio
from loguru import logger

from dorobot.plugin import Message
from dorobot.session_manager import session_manager
from dorobot.bot import Bot
from dorobot.bot_manager import bot_manager
import dorobot.context as ctx


class MessageRouter:
    """消息路由器

    核心职责：
    1. 管理所有 Bot（通过 Bot 实例直接管理）
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
        logger.info("MessageRouter initialized")

    def register_bot(self, bot_id: str) -> bool:
        """注册一个 Bot 到路由系统

        从 bot_manager 获取 Bot 并设置消息回调。

        Args:
            bot_id: Bot 的唯一标识

        Returns:
            bool: 是否注册成功
        """
        bot = bot_manager.get_bot(bot_id)
        if not bot:
            logger.error(f"Bot '{bot_id}' not found in bot_manager")
            return False

        # 创建绑定该 bot 的回调
        async def callback(session_id: str, message: dict):
            await self._handle_bot_message(bot_id, session_id, message)

        bot.on("msg", callback)
        logger.info(f"Registered bot to router: {bot_id} ({bot.__class__.__name__})")
        return True

    def get_bot(self, bot_id: str) -> Bot | None:
        """获取指定 bot_id 的 Bot 实例"""
        return bot_manager.get_bot(bot_id)

    # ========== 消息处理 ==========

    async def _handle_bot_message(self, bot_id: str, session_id: str, message_data: dict) -> bool:
        """处理 Bot 发来的消息

        Args:
            bot_id: Bot 的唯一标识
            session_id: 会话ID
            message_data: 原始消息数据

        Returns:
            bool: 消息是否被完全处理
        """
        bot = bot_manager.get_bot(bot_id)
        if not bot:
            logger.error(f"Bot '{bot_id}' not found")
            return False

        # 通过 SessionManager 获取或创建会话
        session = await self._session_manager.get_or_create_session(bot_id, session_id)

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
            logger.debug(f"[Router] Routing message: bot={bot_id}, session={session_id}, sender={message.sender_name}, content='{content_preview}'")
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
