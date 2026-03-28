"""DoroBot - 多插件聊天机器人核心库"""

from .plugin import Plugin, Message
from .layer import Layer
from .session import Session
from .session_manager import SessionManager, session_manager
from .plugin_manager import PluginManager, plugin_manager, register_plugin
from .router import MessageRouter, router
from .bot import Bot
from .bot_manager import BotManager, bot_manager, register_bot
from .bots.console_bot import ConsoleBot
from .utils import init_logging, load_plugins
from . import context

# 导入内置插件
from .meta_plugin import MetaPlugin
