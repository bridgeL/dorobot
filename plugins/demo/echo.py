"""回声插件"""

from dorobot import Plugin, Message


app = Plugin(name="echo", layer=1, description="回声插件 - /echo 后跟文本，Bot 会原样回复")


@app.on_command("echo")
async def handle(msg: Message, arg: str) -> bool:
    await app.send_message(arg)
    return False


app.register()
