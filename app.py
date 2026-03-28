"""多插件聊天机器人 - 启动入口"""
from dorobot import init_logging, load_plugins, register_bot, run
from dorobot.bots.console import ConsoleBot

# 初始化日志
init_logging(level="DEBUG")

# 加载插件
load_plugins()

# 注册 Bot
register_bot(ConsoleBot())

# 启动程序
run()
