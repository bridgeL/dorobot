"""字频统计插件"""

from collections import Counter
from dorobot import Plugin, Message


app = Plugin(name="字频统计", layer=3, description="统计群里各成员的字频")


@app.on_message()
async def handle(msg: Message) -> bool:
    char_space = app.get_space(memory=False)

    if msg.content.strip() == "/result":
        if not char_space:
            await app.send_message("暂无字频数据")
        else:
            top10 = Counter(dict(char_space)).most_common(10)
            lines = [f"📊 本群字频 Top10："]
            for i, (char, count) in enumerate(top10, 1):
                lines.append(f"  {i}.「{char}」×{count}")
            await app.send_message("\n".join(lines))
        return False

    for char in msg.content:
        if char.strip():
            char_space[char] = char_space.get(char, 0) + 1
    return True


app.register()
