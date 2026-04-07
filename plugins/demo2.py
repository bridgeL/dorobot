"""示例插件集合 2"""

from dorobot import on_command, on_keyword, Message, Plugin


@on_command("/echo", description="回声插件")
async def echo(message: Message, plugin: Plugin, args: str):
    """回声插件 - 回复去掉命令后的内容"""
    await plugin.send_message(args)


@on_keyword("天气", description="查询天气")
async def weather(message: Message, plugin: Plugin):
    """查询天气示例"""
    await plugin.send_message(f"{message.sender_name}，今天天气晴朗，温度 20-28°C！")
