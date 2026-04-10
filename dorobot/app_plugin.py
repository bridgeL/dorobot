"""AppPlugin - 基于状态的插件框架

提供一组装饰器来注册不同状态下的处理函数，简化插件开发。
"""
import re
from typing import Callable, Optional
from loguru import logger

from .message import Message
from .plugin import Plugin
from .config import global_config
from .context import get_session_id
from .plugin_manager import plugin_manager


class AppPlugin(Plugin):
    """基于状态的插件框架

    为每个会话维护独立的状态，handlers 只在当前状态匹配时触发。
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        bots: list[type] | None = None,
        scope: str | None = None,
        active: bool = False,
    ):
        """初始化 AppPlugin

        Args:
            name: 插件名称，唯一标识
            description: 插件描述
            bots: 允许使用该插件的 Bot 类型列表
            scope: 生效范围，None=全部, "private"=仅私聊, "group"=仅群聊
            active: 是否默认激活，默认 True
        """
        super().__init__(
            name=name,
            layer=2,
            description=description,
            bots=bots,
            scope=scope,
            default_active=active,
        )

        # 每个会话的状态，默认为 "idle"
        self._state_dict: dict[str, str] = {}

        # 注册的处理函数 {state: {type: {key: func}}}
        # type: "command", "msg", "pattern", "keyword"
        self._handlers: dict[str, dict[str, dict[str, Callable]]] = {}

        # open/close 回调
        self._on_open: Optional[Callable] = None
        self._on_close: Optional[Callable] = None

    def _state_matches(self, current_state: str, pattern: str | None) -> bool:
        """检查当前状态是否匹配模式

        Args:
            current_state: 当前状态，如 "game.stage1"
            pattern: 模式，如 "game"、"game.*" 或 None（匹配所有）

        Returns:
            bool: 是否匹配
        """
        if pattern is None:
            return True  # None 匹配所有状态
        if current_state == pattern:
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return current_state == prefix or current_state.startswith(prefix + ".")
        return False

    def set_state(self, state: str, session_id: Optional[str] = None):
        """设置当前会话的状态

        Args:
            state: 新状态，如 "game.stage1"
            session_id: 会话ID，None 则使用当前上下文
        """
        if session_id is None:
            session_id = get_session_id()
        if session_id:
            self._state_dict[session_id] = state
            logger.debug(f"[AppPlugin:{self.name}] state changed to '{state}' in session {session_id}")

    def get_state(self, session_id: Optional[str] = None) -> str:
        """获取当前会话的状态

        Args:
            session_id: 会话ID，None 则使用当前上下文

        Returns:
            str: 当前状态，默认为空字符串
        """
        if session_id is None:
            session_id = get_session_id()
        return self._state_dict.get(session_id, "idle")

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

    def on_command(self, state: str | list[str] | None, cmd: str | list[str]):
        """装饰器：注册命令处理函数

        只有当当前状态匹配时，命令才会触发。state 为 None 时匹配所有状态。

        Args:
            state: 状态模式，如 "room"、["room", "game"]，或 None（匹配所有）
            cmd: 命令名称（不含前缀），可以是字符串或列表

        示例：
            @app.on_command(["room", "game"], "start")
            @app.on_command("game", ["play", "出牌"])
            async def handle(message, args):
                ...
        """
        def decorator(func: Callable):
            for s in (state if isinstance(state, list) else [state]):
                key = s if s is not None else "*"
                if key not in self._handlers:
                    self._handlers[key] = {"command": {}, "msg": {}, "pattern": {}, "keyword": {}}
                for c in (cmd if isinstance(cmd, list) else [cmd]):
                    self._handlers[key]["command"][c] = func
            return func
        return decorator

    def on_msg(self, state: str | list[str] | None):
        """装饰器：注册消息处理函数

        只有当当前状态匹配时，消息才会触发。state 为 None 时匹配所有状态。

        Args:
            state: 状态模式，如 "room"、["room", "game"]，或 None（匹配所有）

        示例：
            @app.on_msg(["room", "game"])
            async def handle(message):
                ...
        """
        def decorator(func: Callable):
            for s in (state if isinstance(state, list) else [state]):
                key = s if s is not None else "*"
                if key not in self._handlers:
                    self._handlers[key] = {"command": {}, "msg": {}, "pattern": {}, "keyword": {}}
                self._handlers[key]["msg"]["*"] = func
            return func
        return decorator

    def on_pattern(self, state: str | list[str] | None, pattern: str):
        """装饰器：注册正则匹配处理函数

        只有当当前状态匹配时，正则匹配才会触发。state 为 None 时匹配所有状态。

        Args:
            state: 状态模式，如 "game"、["game", "debug"]，或 None（匹配所有）
            pattern: 正则表达式

        示例：
            @app.on_pattern(["game", "debug"], r"^play (\w+)$")
            async def handle(message, match):
                ...
        """
        def decorator(func: Callable):
            for s in (state if isinstance(state, list) else [state]):
                key = s if s is not None else "*"
                if key not in self._handlers:
                    self._handlers[key] = {"command": {}, "msg": {}, "pattern": {}, "keyword": {}}
                self._handlers[key]["pattern"][pattern] = func
            return func
        return decorator

    def on_keyword(self, state: str | list[str] | None, keyword: str):
        """装饰器：注册关键词处理函数

        只有当当前状态匹配时，关键词才会触发。state 为 None 时匹配所有状态。

        Args:
            state: 状态模式，如 "game"、["game", "debug"]，或 None（匹配所有）
            keyword: 关键词

        示例：
            @app.on_keyword(["game", "debug"], "帮助")
            async def handle(message):
                ...
        """
        def decorator(func: Callable):
            for s in (state if isinstance(state, list) else [state]):
                key = s if s is not None else "*"
                if key not in self._handlers:
                    self._handlers[key] = {"command": {}, "msg": {}, "pattern": {}, "keyword": {}}
                self._handlers[key]["keyword"][keyword] = func
            return func
        return decorator

    async def handle_message(self, message: Message) -> bool:
        session = self.get_session()
        session_id = session.session_id if session else ""
        current_state = self.get_state(session_id)

        # 收集所有匹配状态的处理函数
        matched_handlers: list[tuple[str, Callable, any]] = []

        for state_pattern, handlers_by_type in self._handlers.items():
            if not self._state_matches(current_state, state_pattern):
                continue

            content = message.content.strip()
            cmd_prefix = global_config.cmd_prefix

            # 检查命令
            for cmd, func in handlers_by_type["command"].items():
                full_cmd = f"{cmd_prefix}{cmd}"
                if content == full_cmd or content.startswith(f"{full_cmd} "):
                    args = content[len(full_cmd):].lstrip() if len(content) > len(full_cmd) else ""
                    matched_handlers.append(("command", func, args))
                    break

            # 检查消息
            if "*" in handlers_by_type["msg"]:
                matched_handlers.append(("msg", handlers_by_type["msg"]["*"], None))

            # 检查正则
            for pattern, func in handlers_by_type["pattern"].items():
                match = re.match(pattern, content)
                if match:
                    matched_handlers.append(("pattern", func, match))
                    break

            # 检查关键词
            for keyword, func in handlers_by_type["keyword"].items():
                if keyword in content:
                    matched_handlers.append(("keyword", func, None))
                    break

        # 执行匹配的处理函数
        for htype, handler, arg in matched_handlers:
            try:
                if htype == "command":
                    await handler(message, arg)
                elif htype == "msg":
                    await handler(message)
                elif htype == "pattern":
                    await handler(message, arg)
                elif htype == "keyword":
                    await handler(message)
            except Exception as e:
                logger.error(f"[AppPlugin:{self.name}] handler error: {e}")

        # 如果有匹配的处理函数，返回 False 中断传递
        return len(matched_handlers) == 0

    async def on_activate(self):
        # 设置初始状态为 "idle"
        session = self.get_session()
        session_id = session.session_id if session else ""
        if session_id:
            self._state_dict[session_id] = "idle"
        # 调用 on_open 回调
        if self._on_open:
            try:
                await self._on_open()
            except Exception as e:
                logger.error(f"[AppPlugin:{self.name}] on_open error: {e}")

    def on_deactivate(self):
        # 调用 on_close 回调
        if self._on_close:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(self._on_close):
                    asyncio.create_task(self._on_close())
                else:
                    self._on_close()
            except Exception as e:
                logger.error(f"[AppPlugin:{self.name}] on_close error: {e}")
        # 清理状态
        session = self.get_session()
        session_id = session.session_id if session else ""
        if session_id and session_id in self._state_dict:
            del self._state_dict[session_id]

    def register(self):
        """注册插件到插件管理器"""
        plugin_manager.register(self.name, self, active=self.default_active)
