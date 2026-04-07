"""示例插件集合 2"""

from collections import Counter

from dorobot import on_command, on_keyword, on_message, Message, Plugin, Space


@on_command("echo")
async def echo(message: Message, plugin: Plugin, args: str):
    """回声插件 - 回复去掉命令后的内容"""
    await plugin.send_message(args)


@on_keyword("天气")
async def weather(message: Message, plugin: Plugin):
    """查询天气示例"""
    await plugin.send_message(f"{message.sender_name}，今天天气晴朗，温度 20-28°C！")


@on_message(name="字频统计")
async def char_freq(message: Message, plugin: Plugin):
    """统计群里各成员的字频，用 Space 持久化"""
    session_id = message.raw_data.get("session_id", "") if message.raw_data else ""
    if not session_id:
        return

    char_space = Space("char_freq", session_id)

    for char in message.content:
        if char.strip():  # 只统计非空白字符
            char_space[char] = char_space.get(char, 0) + 1


@on_command("result", name="字频统计结果")
async def show_char(message: Message, plugin: Plugin, args: str):
    """查看字频统计"""
    session_id = message.raw_data.get("session_id", "") if message.raw_data else ""
    if not session_id:
        return

    char_space = Space("char_freq", session_id)

    if not char_space:
        await plugin.send_message("暂无字频数据")
        return

    top10 = Counter(dict(char_space)).most_common(10)
    lines = [f"📊 本群字频 Top10："]
    for i, (char, count) in enumerate(top10, 1):
        lines.append(f"  {i}.「{char}」×{count}")
    await plugin.send_message("\n".join(lines))
