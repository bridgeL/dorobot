"""多插件聊天机器人 - 启动入口"""

from dorobot import Dorobot
from dorobot.adapters.ai_test import AITestAdapter
from dorobot.adapters.console import ConsoleAdapter

dorobot = Dorobot()
dorobot.init()
dorobot.add_adapter(AITestAdapter())
dorobot.add_adapter(ConsoleAdapter())
dorobot.load_plugins()
dorobot.run_forever()
