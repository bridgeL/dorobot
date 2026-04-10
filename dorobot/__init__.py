"""DoroBot - 多插件聊天机器人核心库"""

from .message import Message
from .plugin import Plugin
from .layer import Layer
from .session import Session
from .session_manager import SessionManager, session_manager
from .plugin_manager import PluginManager, plugin_manager, register_plugin
from .router import MessageRouter, router
from .bot import Bot
from .adapter import Adapter
from .bot_manager import BotManager, bot_manager
from .adapter_manager import AdapterManager, adapter_manager
from .utils import init_logging, load_plugins, run, init_space
from . import context as ctx
from .on import on_command, on_keyword, on_pattern, on_message
from .space import Space
from .space_manager import SpaceManager, space_manager
from .config import global_config
from .app_plugin import AppPlugin

def register_adapter(adapter: Adapter) -> bool:
    """注册适配器

    Args:
        adapter: 适配器实例

    Returns:
        bool: 是否注册成功
    """
    return adapter_manager.register(adapter)
