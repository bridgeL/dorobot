"""多插件聊天机器人 - 启动入口"""

from dorobot import init_logging, load_plugins, run, register_adapter

init_logging(level="DEBUG")

load_plugins()

# 命令行调试
# from dorobot.adapters.console import ConsoleAdapter
# register_adapter(ConsoleAdapter())

# NTQQ
from dorobot.adapters.ntqq import NTQQAdapter

register_adapter(NTQQAdapter(port=8082))

run()
