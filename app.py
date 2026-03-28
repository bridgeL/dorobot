"""多插件聊天机器人 - 启动入口"""
from dorobot import init_logging, load_plugins, run, register_adapter
from dorobot.adapters.console import ConsoleAdapter
from dorobot.adapters.ntqq import NTQQAdapter

init_logging(level="DEBUG")

load_plugins()

register_adapter(ConsoleAdapter())
register_adapter(NTQQAdapter())

run()