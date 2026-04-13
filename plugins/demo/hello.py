"""问候插件"""

from dorobot import Plugin, Message


app = Plugin(name="hello", layer=1, description="问候插件", default_active=True)


@app.on_message()
async def handle(msg: Message) -> bool:
    content = msg.content.lower()
    if any(kw in content for kw in ["你好", "hello"]):
        await app.send_message(f"👋 你好，{msg.sender_name}！")
        return False
    return True


app.register()
