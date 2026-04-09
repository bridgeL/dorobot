'''这里提供一组快速创建插件的装饰器'''

from collections.abc import Callable
from typing import Any
import re
from re import Match

from .plugin import Plugin, Message
from .plugin_manager import register_plugin
from .config import global_config


def on_command(cmd: str, description: str = "", layer: int = 1, name: str | None = None, scope: str | None = None, active: bool = True):
    """快速创建命令插件的装饰器

    使用示例：
        @on_command("echo")
        async def handle(message: Message, plugin: Plugin, args: str):
            await plugin.send_message(args)

    Args:
        cmd: 命令字符串，如 "echo"
        description: 插件描述，默认为函数注释第一行
        layer: 所属层级，默认 1
        name: 插件名称，默认使用函数名
        scope: 生效范围，None=全部, "private"=仅私聊, "group"=仅群聊
        active: 是否默认激活，默认 True
    """
    prefix = global_config.cmd_prefix
    full_cmd = f"{prefix}{cmd}"

    def decorator(func: Callable[[Message, Plugin, str], Any]):
        plugin_name = name if name is not None else func.__name__
        desc = description if description else (func.__doc__ or "").strip().split("\n")[0]

        @register_plugin(plugin_name, layer=layer, description=desc, scope=scope, active=active)
        class _CommandPlugin(Plugin):
            async def handle_message(self, message: Message) -> bool:
                stripped = message.content.strip()
                if stripped == full_cmd or stripped.startswith(f"{full_cmd} "):
                    args = stripped[len(full_cmd):].lstrip() if len(stripped) > len(full_cmd) else ""
                    await func(message, self, args)
                    return False
                return True

        return func
    return decorator


def on_keyword(keyword: str, description: str = "", layer: int = 1, name: str | None = None, scope: str | None = None, active: bool = True):
    """快速创建关键词插件的装饰器

    使用示例：
        @on_keyword("hello")
        async def handle(message: Message, plugin: Plugin):
            await plugin.send_message("你好！")

    Args:
        keyword: 关键词，消息包含该关键词时触发
        description: 插件描述，默认为函数注释第一行
        layer: 所属层级，默认 1
        name: 插件名称，默认使用函数名
        scope: 生效范围，None=全部, "private"=仅私聊, "group"=仅群聊
        active: 是否默认激活，默认 True
    """
    def decorator(func: Callable[[Message, Plugin], Any]):
        plugin_name = name if name is not None else func.__name__
        desc = description if description else (func.__doc__ or "").strip().split("\n")[0]

        @register_plugin(plugin_name, layer=layer, description=desc, scope=scope, active=active)
        class _KeywordPlugin(Plugin):
            async def handle_message(self, message: Message) -> bool:
                if keyword.lower() in message.content.lower():
                    await func(message, self)
                    return False
                return True

        return func
    return decorator


def on_pattern(pattern: str, description: str = "", layer: int = 1, name: str | None = None, scope: str | None = None, active: bool = True):
    """快速创建正则匹配插件的装饰器

    使用示例：
        @on_pattern(r"^/echo (.+)$")
        async def handle(message: Message, plugin: Plugin, match):
            await plugin.send_message(match.group(1))

    Args:
        pattern: 正则表达式字符串
        description: 插件描述，默认为函数注释第一行
        layer: 所属层级，默认 1
        name: 插件名称，默认使用函数名
        scope: 生效范围，None=全部, "private"=仅私聊, "group"=仅群聊
        active: 是否默认激活，默认 True
    """
    def decorator(func: Callable[[Message, Plugin, Match[str]], Any]):
        plugin_name = name if name is not None else func.__name__
        desc = description if description else (func.__doc__ or "").strip().split("\n")[0]
        compiled = re.compile(pattern)

        @register_plugin(plugin_name, layer=layer, description=desc, scope=scope, active=active)
        class _PatternPlugin(Plugin):
            async def handle_message(self, message: Message) -> bool:
                match = compiled.match(message.content.strip())
                if match:
                    await func(message, self, match)
                    return False
                return True

        return func
    return decorator


def on_message(description: str = "", layer: int = 3, name: str | None = None, scope: str | None = None, active: bool = True):
    """快速创建通用消息处理插件的装饰器

    每次收到消息都会触发，适用于统计、监控等需要处理所有消息的场景。

    使用示例：
        @on_message()
        async def handle(message: Message, plugin: Plugin):
            print(f"收到消息: {message.content}")

    Args:
        description: 插件描述，默认为函数注释第一行
        layer: 所属层级，默认 3（兜底层）
        name: 插件名称，默认使用函数名
        scope: 生效范围，None=全部, "private"=仅私聊, "group"=仅群聊
        active: 是否默认激活，默认 True
    """
    def decorator(func: Callable[[Message, Plugin], Any]):
        plugin_name = name if name is not None else func.__name__
        desc = description if description else (func.__doc__ or "").strip().split("\n")[0]

        @register_plugin(plugin_name, layer=layer, description=desc, scope=scope, active=active)
        class _MessagePlugin(Plugin):
            async def handle_message(self, message: Message) -> bool:
                await func(message, self)
                return True  # 继续传递，不中断

        return func
    return decorator
