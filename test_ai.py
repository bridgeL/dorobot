"""多插件聊天机器人 - 启动入口"""

from dorobot import Dorobot
from dorobot.adapters.ai_test import AITestAdapter

dorobot = Dorobot()
dorobot.init()
dorobot.add_adapter(AITestAdapter())
dorobot.load_plugins()
dorobot.run_forever()
