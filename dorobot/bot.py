"""Bot 基类定义

定义 Bot 的标准接口，所有 Bot 实现必须继承此类。
"""
from abc import ABC, abstractmethod
from typing import Callable, Awaitable


class Bot(ABC):
    """Bot 抽象基类

    所有 Bot 实现必须继承此类并提供:
    - send: 发送消息到会话
    - on: 注册事件处理器
    """

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    @abstractmethod
    async def send(self, session_id: str, content: str):
        """发送消息到指定会话

        Args:
            session_id: 会话唯一标识
            content: 消息内容
        """
        pass

    def on(self, event_name: str, callback: Callable[..., Awaitable[None]]):
        """注册事件处理器

        Args:
            event_name: 事件名称，如 "msg", "join", "leave" 等
            callback: 异步回调函数，接收事件数据
        """
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(callback)
        return self

    async def emit(self, event_name: str, *args, **kwargs):
        """触发事件

        调用所有注册的事件处理器。

        Args:
            event_name: 事件名称
            *args, **kwargs: 传递给回调函数的参数
        """
        handlers = self._handlers.get(event_name, [])
        for handler in handlers:
            try:
                await handler(*args, **kwargs)
            except Exception as e:
                self._on_handler_error(event_name, handler, e)

    def _on_handler_error(self, event_name: str, handler: Callable, error: Exception):
        """处理回调错误，子类可重写"""
        pass

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
