"""Bot 基类定义

定义 Bot 的标准接口，所有 Bot 实现必须继承此类。
"""
from abc import ABC, abstractmethod


class Bot(ABC):
    """Bot 抽象基类

    所有 Bot 实现必须继承此类并提供:
    - send: 发送消息到会话
    - on_message: 处理收到的消息（调用 router.handle_message）
    """

    def __init__(self, self_id: str = ""):
        self.self_id: str = self_id

    @abstractmethod
    async def send(self, session_id: str, content: str):
        """发送消息到指定会话

        Args:
            session_id: 会话唯一标识
            content: 消息内容
        """
        pass

    async def on_message(self, session_id: str, message_data: dict):
        """处理收到的消息

        Bot 收到消息后应调用此方法，它会将消息路由到插件系统。

        Args:
            session_id: 会话ID
            message_data: 消息数据字典，包含 content, sender_id, sender_name, msg_type 等
        """
        from .router import router
        await router.handle_message(self.self_id, session_id, message_data)

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