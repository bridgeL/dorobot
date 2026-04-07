'''这里提供一组快速创建插件的装饰器'''

from collections.abc import Callable
from typing import Any

from dorobot.plugin import Plugin, Message
from dorobot.plugin_manager import register_plugin


def on_command(cmd: str, description: str = "", layer: int = 1, name: str | None = None):
    """快速创建命令插件的装饰器

    使用示例：
        @on_command("/echo", "回声插件")
        async def handle(message: Message, plugin: Plugin, args: str):
            await plugin.send_message(args)

        # 或指定插件名
        @on_command("/echo", "回声插件", name="my_echo")
        async def handle(message: Message, plugin: Plugin, args: str):
            await plugin.send_message(args)

    Args:
        cmd: 命令字符串，如 "/echo"
        description: 插件描述
        layer: 所属层级，默认 1
        name: 插件名称，默认使用函数名
    """
    def decorator(func: Callable[[Message, Plugin, str], Any]):
        plugin_name = name if name is not None else func.__name__

        @register_plugin(plugin_name, layer=layer, description=description)
        class _CommandPlugin(Plugin):
            async def handle_message(self, message: Message) -> bool:
                stripped = message.content.strip()
                if stripped == cmd or stripped.startswith(f"{cmd} "):
                    args = stripped[len(cmd):].lstrip() if len(stripped) > len(cmd) else ""
                    await func(message, self, args)
                    return False
                return True

        return func
    return decorator


def on_keyword(keyword: str, description: str = "", layer: int = 1, name: str | None = None):
    """快速创建关键词插件的装饰器

    使用示例：
        @on_keyword("hello", "问候插件")
        async def handle(message: Message, plugin: Plugin):
            await plugin.send_message(f"你好，{message.sender_name}！")

        # 或指定插件名
        @on_keyword("hello", "问候插件", name="my_greeting")
        async def handle(message: Message, plugin: Plugin):
            await plugin.send_message(f"你好，{message.sender_name}！")

    Args:
        keyword: 关键词，消息包含该关键词时触发
        description: 插件描述
        layer: 所属层级，默认 1
        name: 插件名称，默认使用函数名
    """
    def decorator(func: Callable[[Message, Plugin], Any]):
        plugin_name = name if name is not None else func.__name__

        @register_plugin(plugin_name, layer=layer, description=description)
        class _KeywordPlugin(Plugin):
            async def handle_message(self, message: Message) -> bool:
                if keyword.lower() in message.content.lower():
                    await func(message, self)
                    return False
                return True

        return func
    return decorator


def on_pattern(pattern: str, description: str = "", layer: int = 1, name: str | None = None):
    """快速创建正则匹配插件的装饰器

    使用示例：
        @on_pattern(r"^/echo (.+)$", "回声插件")
        async def handle(message: Message, plugin: Plugin, match: Match[str]):
            await plugin.send_message(match.group(1))

        # 或指定插件名
        @on_pattern(r"^/echo (.+)$", "回声插件", name="my_echo")
        async def handle(message: Message, plugin: Plugin, match: Match[str]):
            await plugin.send_message(match.group(1))

    Args:
        pattern: 正则表达式字符串
        description: 插件描述
        layer: 所属层级，默认 1
        name: 插件名称，默认使用函数名
    """
    import re
    from re import Match

    def decorator(func: Callable[[Message, Plugin, Match[str]], Any]):
        plugin_name = name if name is not None else func.__name__
        compiled = re.compile(pattern)

        @register_plugin(plugin_name, layer=layer, description=description)
        class _PatternPlugin(Plugin):
            async def handle_message(self, message: Message) -> bool:
                match = compiled.match(message.content.strip())
                if match:
                    await func(message, self, match)
                    return False
                return True

        return func
    return decorator
