"""插件基类定义"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from loguru import logger

import dorobot.context as ctx
from dorobot.space import Space


@dataclass
class Message:
    """消息数据类"""

    content: str
    sender_id: str
    sender_name: str
    msg_type: str = "text"  # text, image, etc.
    raw_data: Optional[dict] = None


class Plugin(ABC):
    """插件基类

    所有插件必须继承此类并实现相关方法。
    插件是全局独立实例，不绑定特定 session。
    哪个 session 激活了该插件，handle_message 就接收哪个 session。
    """

    def __init__(
        self,
        name: str,
        layer: int = 2,
        description: str = "",
        bots: list[type] | None = None,
    ):
        """初始化插件

        Args:
            name: 插件名称，唯一标识
            layer: 碰撞层，默认2层（应用层，独占）
            description: 插件描述
            bots: 允许使用该插件的 Bot 类型列表，None 表示允许所有 Bot
        """
        self.name = name
        self.layer = layer
        self.description = description
        self.bots = bots

    @abstractmethod
    async def handle_message(self, message: Message) -> bool:
        """处理消息

        Args:
            message: 消息对象

        Returns:
            bool: True表示继续传递消息到下一层，False表示中断传递
        """
        pass

    async def on_activate(self):
        """插件被激活时调用

        子类可重写此方法，在插件被激活时执行初始化逻辑。
        例如：初始化状态、加载数据等。
        """
        pass

    def get_session(self):
        """获取当前 Session 对象

        插件可以通过此方法获取当前会话，读写 session.data。
        不在消息处理上下文中时返回 None。
        """
        from dorobot.session_manager import session_manager

        return session_manager.get_session(ctx.get_session_id())

    def get_bot(self):
        """获取当前 Bot 对象

        插件可以通过此方法获取当前 Bot 实例。
        不在消息处理上下文中时返回 None。
        """
        from dorobot.bot_manager import bot_manager

        return bot_manager.get_bot(ctx.get_bot_id())

    async def send_message(
        self, content: str, session_id: str | None = None, bot_id: str | None = None
    ):
        """发送消息到当前会话

        通过 MessageRouter 发送消息。

        Args:
            content: 消息内容
            session_id: 目标会话ID，None 则使用当前上下文中的 session_id
            bot_id: Bot 的唯一标识，None 则从上下文获取
        """
        from dorobot.bot_manager import bot_manager

        if bot_id is None:
            bot_id = ctx.get_bot_id()

        if not bot_id:
            logger.warning(
                f"Plugin {self.name} has no bot context, cannot send message"
            )
            return

        if session_id is None:
            session_id = ctx.get_session_id()

        if not session_id:
            logger.warning(
                f"Plugin {self.name} has no session context, cannot send message"
            )
            return

        # 从 bot_manager 获取 bot 并发送消息
        bot = bot_manager.get_bot(bot_id)
        if bot:
            await bot.send(session_id, content)
        else:
            logger.warning(f"Plugin {self.name}: bot '{bot_id}' not found")
