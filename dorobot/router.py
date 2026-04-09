"""消息路由系统

连接Bot和插件系统，负责消息的分发和路由。
协调 BotManager 和 SessionManager 的关系。
"""
from loguru import logger

from .plugin import Message
from .session_manager import session_manager
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

    def __init__(self):
        """初始化消息路由器"""
        self._session_manager = session_manager

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
        # 设置上下文变量
        context.bot_id.set(bot_id)
        context.session_id.set(session_id)

        try:
            # 通过 SessionManager 获取或创建会话
            session = await self._session_manager.get_or_create_session(
                session_id,
                type=message_data.get("type", "private"),
                group_id=message_data.get("group_id", ""),
                user_id=message_data.get("user_id", ""),
            )
            
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


# 全局 MessageRouter 实例
router = MessageRouter()
