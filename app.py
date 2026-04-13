"""多插件聊天机器人 - 启动入口"""

from dorobot import Dorobot
from dorobot.adapters.ntqq import NTQQAdapter

dorobot = Dorobot()
dorobot.init()
dorobot.add_adapter(NTQQAdapter())
dorobot.load_plugins()
dorobot.run_forever()
