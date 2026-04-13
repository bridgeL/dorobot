"""Bot 基类定义

定义 Bot 的标准接口，所有 Bot 实现必须继承此类。
"""

from abc import ABC, abstractmethod

from .message import Message


class Bot(ABC):
    """Bot 抽象基类

    所有 Bot 实现必须继承此类并提供:
    - send: 发送消息到会话
    - on_message: 处理收到的消息（调用 router.handle_message）
    """

    def __init__(self, self_id: str = ""):
        self.self_id: str = self_id
        self._dorobot: "Dorobot" = None  # type: ignore[name-defined]

    @abstractmethod
    async def send(self, session_id: str, content: str):
        """发送消息到指定会话

        Args:
            session_id: 会话唯一标识
            content: 消息内容
        """
        pass

    @abstractmethod
    async def send_group(self, group_id: str, content: str):
        """发送群消息

        Args:
            group_id: 群组ID
            content: 消息内容
        """
        pass

    @abstractmethod
    async def send_private(self, user_id: str, content: str):
        """发送私聊消息

        Args:
            user_id: 用户ID
            content: 消息内容
        """
        pass

    async def on_message(self, message: Message):
        """处理收到的消息

        Bot 收到消息后应调用此方法，它会将消息路由到插件系统。

        Args:
            message: 消息对象
        """
        if not self._dorobot:
            return
        await self._dorobot.router.handle_message(self.self_id, message)

    @abstractmethod
    async def start(self):
        """启动 Bot

        开始接收消息/事件。
        """
        pass

    @abstractmethod
    async def stop(self):
        """停止 Bot

        停止接收消息/事件，清理资源。
        """
        pass
