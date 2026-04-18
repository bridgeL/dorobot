"""插件基类定义"""

import re
from abc import ABC
from typing import Callable, Optional
from loguru import logger

from .context import get_bot_id, get_session_id
from .message import Message
from .space import Space


class Plugin(ABC):
    """插件基类

    所有插件必须继承此类并实现相关方法。
    插件是全局独立实例，不绑定特定 session。
    哪个 session 激活了该插件，handle_message 就接收哪个 session。
    """

    def __init__(
        self,
        name: str,
        layer: int = 1,
        description: str = "",
        bots: list[type] | None = None,
        scope: str | None = None,
        default_active: bool = True,
    ):
        """初始化插件

        Args:
            name: 插件名称，唯一标识
            layer: 碰撞层，默认2层（应用层，独占）
            description: 插件描述
            bots: 允许使用该插件的 Bot 类型列表，None 表示允许所有 Bot
            scope: 生效范围，None=全部, "private"=仅私聊, "group"=仅群聊
            default_active: 是否默认激活，默认 True
        """
        self.name = name
        self.layer = layer
        self.description = description
        self.bots = bots
        self.scope = scope  # None=全部, "private"=仅私聊, "group"=仅群聊
        self.default_active = default_active

        # open/close 回调
        self._on_open: Optional[Callable] = None
        self._on_close: Optional[Callable] = None

        # 消息处理回调
        self._handler: Optional[Callable[[Message], bool]] = None
        # 命令处理回调 {cmd: handler}
        self._command_handlers: dict[str, Callable[[Message, str], bool]] = {}
        # 正则处理回调 {pattern: (compiled_regex, handler)}
        self._regex_handlers: dict[str, tuple[re.Pattern, Callable[[Message, re.Match], bool]]] = {}

    def register(self) -> bool:
        """注册插件到插件管理器

        Returns:
            bool: 是否注册成功，重名则返回 False
        """
        from .plugin_manager import plugin_manager
        return plugin_manager.register(self.name, self)

    def on_message(self):
        """装饰器：注册消息处理函数

        使用方式：
            @app.on_message()
            async def handle(message):
                ...
                return True  # 返回 True 继续传递，False 中断
        """
        def decorator(func: Callable[[Message], bool]):
            self._handler = func
            return func
        return decorator

    def on_command(self, cmd: str):
        """装饰器：注册命令处理函数

        使用方式：
            @app.on_command("start")
            async def handle(message, args):
                ...
                return True
        """
        def decorator(func: Callable[[Message, str], bool]):
            self._command_handlers[cmd] = func
            return func
        return decorator

    def on_regex(self, pattern: str):
        """装饰器：注册正则处理函数

        使用方式：
            @app.on_regex(r"^play (\w+)$")
            async def handle(message, match):
                ...
                return True
        """
        def decorator(func: Callable[[Message, re.Match], bool]):
            self._regex_handlers[pattern] = (re.compile(pattern), func)
            return func
        return decorator

    async def handle_message(self, message: Message) -> bool:
        """处理消息（内部调度）

        按 command → regex → msg 顺序匹配并调用处理器。
        任一处理器返回 False 则中断传递。
        """
        from .config import global_config

        content = message.content.strip()
        cmd_prefix = global_config.cmd_prefix
        blocked = False

        # 检查命令
        for cmd, handler in self._command_handlers.items():
            full_cmd = f"{cmd_prefix}{cmd}"
            if content == full_cmd or content.startswith(f"{full_cmd} "):
                args = content[len(full_cmd):].lstrip() if len(content) > len(full_cmd) else ""
                result = await handler(message, args)
                if result is False:
                    blocked = True
                    break
                break

        if not blocked:
            # 检查正则
            for _, (compiled, handler) in self._regex_handlers.items():
                m = compiled.match(content)
                if m:
                    result = await handler(message, m)
                    if result is False:
                        blocked = True
                        break

        if not blocked and self._handler:
            result = await self._handler(message)
            if result is False:
                blocked = True

        return not blocked

    async def handle_activate(self):
        """激活时内部调用，触发 on_open 回调"""
        if self._on_open:
            await self._on_open()

    async def handle_deactivate(self):
        """关闭时内部调用，触发 on_close 回调"""
        from .context import get_dorobot
        dorobot = get_dorobot()
        if dorobot:
            dorobot.session_manager.unmount_plugin_all(self.name)
        if self._on_close:
            result = self._on_close()
            import asyncio
            if asyncio.iscoroutine(result):
                await result

    def on_open(self):
        """装饰器：注册插件启动时的回调

        使用方式：
            @app.on_open()
            async def handle():
                ...
        """
        def decorator(func: Callable):
            self._on_open = func
            return func
        return decorator

    def on_close(self):
        """装饰器：注册插件关闭时的回调

        使用方式：
            @app.on_close()
            async def handle():
                ...
        """
        def decorator(func: Callable):
            self._on_close = func
            return func
        return decorator

    def close_self(self, session_id: str | None = None):
        """请求关闭自身

        将关闭请求添加到 Router，在当前消息处理结束后自动关闭。

        Args:
            session_id: 指定要关闭的 session，不指定则关闭当前 session
        """
        from .context import get_dorobot
        dorobot = get_dorobot()
        if dorobot and dorobot.router:
            target = session_id if session_id else self.get_session().session_id if self.get_session() else None
            if target:
                if self.name not in dorobot.router._close_requests:
                    dorobot.router._close_requests[self.name] = []
                dorobot.router._close_requests[self.name].append((target, self.layer))

    async def mount_to(self, private_session_id: str) -> bool:
        """挂载到指定私聊 session 的 Layer 1（自动创建不存在的 session）

        只有 scope=group 的插件可以发起挂载。

        Args:
            private_session_id: 目标私聊 session_id

        Returns:
            bool: 是否挂载成功
        """
        from .context import get_dorobot

        if self.scope != "group":
            logger.warning(f"[Plugin:{self.name}] mount_to: only scope=group plugins can mount")
            return False

        dorobot = get_dorobot()
        if not dorobot:
            return False
        # 获取当前 session ID（父 session）
        parent_session_id = get_session_id()
        return await dorobot.session_manager.mount_plugin(self.name, private_session_id, parent_session_id)

    def unmount_from(self, private_session_id: str) -> bool:
        """从指定私聊 session 卸载

        Args:
            private_session_id: 目标私聊 session_id

        Returns:
            bool: 是否卸载成功
        """
        from .context import get_dorobot

        dorobot = get_dorobot()
        if not dorobot:
            return False
        return dorobot.session_manager.unmount_plugin(self.name, private_session_id)

    def unmount_from_all(self):
        """取消所有跨 session 挂载"""
        from .context import get_dorobot

        dorobot = get_dorobot()
        if dorobot:
            dorobot.session_manager.unmount_plugin_all(self.name)

    def get_session(self):
        """获取当前 Session 对象

        插件可以通过此方法获取当前会话，读写 session.data。
        不在消息处理上下文中时返回 None。
        """
        from .context import get_dorobot

        dorobot = get_dorobot()
        if not dorobot:
            return None
        return dorobot.session_manager.get_session(get_session_id())

    def get_bot(self):
        """获取当前 Bot 对象

        插件可以通过此方法获取当前 Bot 实例。
        不在消息处理上下文中时返回 None。
        """
        from .context import get_dorobot

        dorobot = get_dorobot()
        if not dorobot:
            return None
        return dorobot.bot_manager.get_bot(get_bot_id())

    def get_space(self, memory: bool = True):
        """获取当前插件在当前会话的 Space

        每个插件在每个会话都有独立的 Space，可用于存储该会话的数据。
        不在消息处理上下文中时返回 None。

        如果当前 session 是通过 mount_to 挂载的子 session，
        则自动返回父 session 的 Space（确保 mounted 插件能访问主 session 数据）。

        Args:
            memory: 是否使用内存模式，默认 True。False 则持久化到磁盘。
        """
        session_id = get_session_id()
        if not session_id:
            return None

        space = Space(self.name, session_id, memory=memory)

        # 检查是否挂载到子 session，若是则返回父 session 的 space
        parent_key = f"_parent_space_{self.name}_"
        parent_session_id = space.get(parent_key)
        if parent_session_id:
            return Space(self.name, parent_session_id, memory=memory)

        return space

    def get_message(self) -> Message | None:
        """获取当前处理的消息

        在 on_open、on_close、on_command、on_message 等回调中可用。
        不在消息处理上下文中时返回 None。

        Returns:
            Message: 当前消息对象
        """
        from .context import get_current_message

        return get_current_message()

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
        from .context import get_dorobot

        if bot_id is None:
            bot_id = get_bot_id()

        if not bot_id:
            logger.warning(
                f"Plugin {self.name} has no bot context, cannot send message"
            )
            return

        if session_id is None:
            session_id = get_session_id()

        if not session_id:
            logger.warning(
                f"Plugin {self.name} has no session context, cannot send message"
            )
            return

        dorobot = get_dorobot()
        if not dorobot:
            return

        # 从 bot_manager 获取 bot 并发送消息
        bot = dorobot.bot_manager.get_bot(bot_id)
        if bot:
            await bot.send(session_id, content)
        else:
            logger.warning(f"Plugin {self.name}: bot '{bot_id}' not found")
