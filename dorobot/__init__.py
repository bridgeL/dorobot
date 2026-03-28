"""DoroBot - 多插件聊天机器人核心库"""

from .plugin import Plugin, Message
from .layer import Layer
from .session import Session
from .session_manager import SessionManager, session_manager
from .plugin_manager import PluginManager, plugin_manager, register_plugin
from .router import MessageRouter, router
from .bot import Bot
from .adapter import Adapter
from .bot_manager import BotManager, bot_manager
from .adapter_manager import AdapterManager, adapter_manager
from .utils import init_logging, load_plugins, run
from . import context

# 导入内置插件
from .meta_plugin import MetaPlugin


def register_adapter(adapter: Adapter) -> bool:
    """注册适配器

    Args:
        adapter: 适配器实例

    Returns:
        bool: 是否注册成功
    """
    return adapter_manager.register(adapter)