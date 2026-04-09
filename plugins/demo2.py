"""示例插件集合 2"""

from dorobot import on_command, on_keyword, Message, Plugin


@on_command("echo", active=False)
async def echo(message: Message, plugin: Plugin, arg: str):
    """回声插件 - 回复去掉命令后的内容"""
    await plugin.send_message(arg)


@on_keyword(["你好", "hello"], active=True)
async def hello(message: Message, plugin: Plugin):
    """问候插件"""
    await plugin.send_message(f"👋 你好，{message.sender_name}！")
