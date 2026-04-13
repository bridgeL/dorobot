"""消息路由系统

连接Bot和插件系统，负责消息的分发和路由。
协调 BotManager 和 SessionManager 的关系。
"""
from loguru import logger

from .message import Message
from . import context


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

    def __init__(self, dorobot: "Dorobot"):
        self._dorobot = dorobot

    async def handle_message(self, bot_id: str, message: Message) -> bool:
        """处理 Bot 发来的消息

        这是 Bot 收到消息后应该调用的入口方法。

        Args:
            bot_id: Bot 的唯一标识
            message: 消息对象

        Returns:
            bool: 消息是否被完全处理
        """
        session_id = message.session_id

        # 设置上下文变量
        context.bot_id.set(bot_id)
        context.session_id.set(session_id)
        context.set_dorobot(self._dorobot)

        try:
            # 通过 SessionManager 获取或创建会话
            session = await self._dorobot.session_manager.get_or_create_session(
                session_id,
                type=message.session_type,
                group_id=message.group_id,
                user_id=message.user_id,
            )

            content_preview = message.content[:50] + "..." if len(message.content) > 50 else message.content
            logger.info(f"[Router] Routing message: bot={bot_id}, session_id={session_id}, sender_id={message.sender_id}, sender_name={message.sender_name}, content={content_preview}', ")
            result = await session.handle_message(message)
            return result
        finally:
            # 清理上下文（可选，因为contextvars会自动处理）
            pass
