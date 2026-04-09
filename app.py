"""多插件聊天机器人 - 启动入口"""

from dorobot import init_logging, load_plugins, run, register_adapter, init_space

init_logging(level="INFO")
init_space()
load_plugins()

# NTQQ
from dorobot.adapters.ntqq import NTQQAdapter
register_adapter(NTQQAdapter(port=8082))

run()
