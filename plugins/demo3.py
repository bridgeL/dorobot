"""Demo3 - AppPlugin 状态机示例

演示如何使用 AppPlugin 实现状态转移：
- idle: 初始状态，等待玩家
- room: 房间已创建，等待玩家加入/开始游戏
- playing: 游戏进行中
- game_over: 游戏结束，可重新开始或解散

状态转移：
  idle -> room (创建房间)
  room -> idle (解散房间)
  room -> playing (开始游戏)
  playing -> room (游戏结束)
  playing -> idle (解散房间)
  game_over -> room (重新开始)
  game_over -> idle (解散房间)
"""

from dorobot import AppPlugin, Message

app = AppPlugin(
    name="房间测试",
    description="AppPlugin 状态机演示",
    scope="group",
)


# ========== 生命周期 ==========


@app.on_open()
async def on_open_handler():
    space = app.get_space()
    space["players"] = []
    await app.send_message("欢迎使用 Demo3 游戏！\n发送【创建房间】开始")


# ========== idle 状态 ==========


@app.on_command("idle", ["创建房间", "创建"])
async def create_room(message: Message, args: str):
    space = app.get_space()
    space["players"] = [(message.sender_id, message.sender_name)]
    app.set_state("room")
    await app.send_message(
        f"房间已创建！\n"
        f"房主: {message.sender_name}\n"
        f"发送【加入】入座\n"
        f"发送【解散】解散房间"
    )


# ========== room 状态 ==========


@app.on_command("room", ["加入", "加入房间"])
async def join_room(message: Message, args: str):
    space = app.get_space()
    players = space.get("players", [])
    if (message.sender_id, message.sender_name) in players:
        await app.send_message("你已经在房间里了")
        return
    players.append((message.sender_id, message.sender_name))
    space["players"] = players
    player_count = len(players)
    msg = f"{message.sender_name} 加入了房间！\n当前玩家: {player_count}人"
    if player_count >= 3:
        msg += "\n可以发送【开始】开始游戏"
    await app.send_message(msg)


@app.on_command("room", ["开始", "开始游戏"])
async def start_game(message: Message, args: str):
    space = app.get_space()
    players = space.get("players", [])
    if len(players) < 3:
        await app.send_message(f"玩家不足，需要至少3人，当前{len(players)}人")
        return
    app.set_state("playing")
    names = "\n".join(f"{i+1}. {name}" for i, (_, name) in enumerate(players))
    await app.send_message(f"游戏开始！\n\n玩家列表:\n{names}\n\n发送【结束】结束游戏")


@app.on_command("room", ["解散", "解散房间"])
async def dismiss_room(message: Message, args: str):
    space = app.get_space()
    space["players"] = []
    app.set_state("idle")
    await app.send_message("房间已解散")


@app.on_command("room", ["离开", "离开房间"])
async def leave_room(message: Message, args: str):
    space = app.get_space()
    players = space.get("players", [])
    if (message.sender_id, message.sender_name) not in players:
        await app.send_message("你不在房间里")
        return
    players.remove((message.sender_id, message.sender_name))
    space["players"] = players
    if len(players) == 0:
        app.set_state("idle")
        await app.send_message("房间已解散（无人）")
    else:
        await app.send_message(
            f"{message.sender_name} 离开了房间，当前{len(players)}人"
        )


@app.on_command("room", "状态")
async def room_status(message: Message, args: str):
    space = app.get_space()
    players = space.get("players", [])
    names = "\n".join(f"{i+1}. {name}" for i, (_, name) in enumerate(players))
    await app.send_message(f"房间状态:\n当前玩家: {len(players)}人\n{names}")


# ========== playing 状态 ==========


@app.on_command("playing", ["结束", "结束游戏"])
async def end_game(message: Message, args: str):
    app.set_state("game_over")
    await app.send_message("游戏结束！\n发送【再来一局】重新开始\n发送【解散】解散房间")


# ========== game_over 状态 ==========


@app.on_command("game_over", ["再来一局", "再来"])
async def restart_game(message: Message, args: str):
    app.set_state("playing")
    space = app.get_space()
    players = space.get("players", [])
    await app.send_message(f"游戏重新开始！\n当前玩家: {len(players)}人")


@app.on_command("game_over", ["解散", "解散房间"])
async def dismiss_after_game(message: Message, args: str):
    space = app.get_space()
    space["players"] = []
    app.set_state("idle")
    await app.send_message("房间已解散")


# ========== 全局命令 ==========


@app.on_command(None, "帮助")
async def show_help(message: Message, args: str):
    state = app.get_state()
    if state == "idle":
        msg = "【帮助】\n创建房间 - 创建新房间"
    elif state == "room":
        msg = "【帮助】\n加入 - 加入房间\n开始 - 开始游戏\n解散 - 解散房间\n离开 - 离开房间\n状态 - 查看房间状态"
    elif state == "playing":
        msg = "【帮助】\n结束 - 结束游戏"
    else:
        msg = "【帮助】\n再来一局 - 重新开始\n解散 - 解散房间"
    await app.send_message(msg)


app.register()
