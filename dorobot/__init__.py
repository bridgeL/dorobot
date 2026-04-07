"""DoroBot - 多插件聊天机器人核心库"""

from dorobot.plugin import Plugin, Message
from dorobot.layer import Layer
from dorobot.session import Session
from dorobot.session_manager import SessionManager, session_manager
from dorobot.plugin_manager import PluginManager, plugin_manager, register_plugin
from dorobot.router import MessageRouter, router
from dorobot.bot import Bot
from dorobot.adapter import Adapter
from dorobot.bot_manager import BotManager, bot_manager
from dorobot.adapter_manager import AdapterManager, adapter_manager
from dorobot.utils import init_logging, load_plugins, run
from dorobot import context as ctx
from loguru import logger

def register_adapter(adapter: Adapter) -> bool:
    """注册适配器

    Args:
        adapter: 适配器实例

    Returns:
        bool: 是否注册成功
    """
    return adapter_manager.register(adapter)
