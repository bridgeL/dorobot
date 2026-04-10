"""犯罪舞蹈 V2 - 房间管理模块"""

from .plugin import app


# ========== 辅助函数 ==========


def _get_room_info() -> dict:
    """获取房间信息"""
    space = app.get_space()
    room = space.get("room", {})
    if not room:
        room = {
            "owner_id": "",
            "owner_name": "",
            "players": [],
            "player_ids": [],
        }
        space["room"] = room
    return room


def _save_room(room: dict):
    """保存房间信息"""
    app.get_space()["room"] = room


def _get_game():
    """获取当前游戏实例"""
    space = app.get_space()
    return space.get("game")


def _save_game(game):
    """保存游戏实例"""
    app.get_space()["game"] = game


def setup_room_space():
    """初始化房间空间（供 on_open 调用）"""
    space = app.get_space()
    space["room"] = {
        "owner_id": "",
        "owner_name": "",
        "players": [],
        "player_ids": [],
    }
    space["game"] = None


# ========== idle 状态 ==========

@app.on_command("idle", ["创建房间", "创建"])
async def cmd_create_room(message, args: str):
    """创建房间"""
    room = _get_room_info()
    if room["owner_id"]:
        await app.send_message("房间已存在，请先解散或加入现有房间")
        return

    room["owner_id"] = message.sender_id
    room["owner_name"] = message.sender_name
    room["players"] = [(message.sender_id, message.sender_name)]
    room["player_ids"] = [message.sender_id]
    _save_room(room)
    app.set_state("room.waiting")

    await app.send_message(
        f"🎭 房间已创建！\n"
        f"房主: {message.sender_name}\n"
        f"等待玩家加入...\n"
        f"发送【加入】入座\n"
        f"发送【状态】查看房间\n"
        f"发送【解散】解散房间"
    )


@app.on_command("idle", ["帮助", "游戏帮助"])
async def cmd_help_idle(message, args: str):
    """idle状态帮助"""
    await app.send_message(
        "🎭 犯罪舞蹈 V2\n"
        "【创建房间】- 创建新房间（房主）\n"
        "【帮助】- 查看游戏规则"
    )


# ========== room.waiting 状态 ==========

@app.on_command("room.waiting", ["加入", "加入房间"])
async def cmd_join(message, args: str):
    """加入房间"""
    room = _get_room_info()

    if message.sender_id in room["player_ids"]:
        await app.send_message("你已经在房间里了")
        return

    room["players"].append((message.sender_id, message.sender_name))
    room["player_ids"].append(message.sender_id)
    _save_room(room)

    player_count = len(room["players"])
    msg = f"✅ {message.sender_name} 加入了房间！\n当前玩家: {player_count}人"
    if player_count >= 3:
        msg += "\n房主可以发送【开始】开始游戏"
    else:
        msg += "\n等待更多玩家加入...（需要至少3人）"
    await app.send_message(msg)


@app.on_command("room.waiting", ["开始", "开始游戏"])
async def cmd_start(message, args: str):
    """开始游戏"""
    room = _get_room_info()

    if message.sender_id != room["owner_id"]:
        await app.send_message("只有房主可以开始游戏")
        return

    num_players = len(room["players"])
    if num_players < 3:
        await app.send_message(f"玩家不足，需要至少3人，当前{num_players}人")
        return

    from .game_core import Game
    from dorobot.space import Space

    # 创建游戏实例
    game_core = Game()
    game_core.reset(num_players)
    game_core.plugin = app
    game_core.group_id = message.group_id or message.sender_id

    # 设置玩家信息
    for i, (player_id, player_name) in enumerate(room["players"]):
        game_core.players[i].player_id = player_id
        game_core.players[i].player_name = player_name

    # 建立私聊映射
    for player_id, _ in room["players"]:
        private_space = Space(app.name, f"private.{player_id}", memory=True)
        private_space["group_session_id"] = app.get_session().session_id

    _save_game(game_core)
    app.set_state("room.starting")

    # 启动游戏（异步发牌）
    await game_core.start()

    # 发牌完毕，切换到游戏状态
    app.set_state("game.play")

    # 通知当前玩家
    current = game_core.current_player
    await app.send_message(
        f"🎮 游戏开始！\n"
        f"公共信息: {num_players}人局\n"
        f"当前回合: {current.player_name}\n"
        f"请 {current.player_name} 发送【出牌】+ 牌名 [@目标]"
    )


@app.on_command("room.waiting", ["解散", "解散房间"])
async def cmd_dismiss(message, args: str):
    """解散房间"""
    room = _get_room_info()

    if message.sender_id != room["owner_id"]:
        await app.send_message("只有房主可以解散房间")
        return

    room["owner_id"] = ""
    room["owner_name"] = ""
    room["players"] = []
    room["player_ids"] = []
    _save_room(room)
    _save_game(None)
    app.set_state("idle")

    await app.send_message("房间已解散")


@app.on_command("room.waiting", ["离开", "离开房间"])
async def cmd_leave(message, args: str):
    """离开房间"""
    room = _get_room_info()

    if message.sender_id not in room["player_ids"]:
        await app.send_message("你不在房间里")
        return

    idx = room["player_ids"].index(message.sender_id)
    leaving_name = room["players"][idx][1]
    room["players"].pop(idx)
    room["player_ids"].pop(idx)

    if message.sender_id == room["owner_id"]:
        if room["players"]:
            room["owner_id"] = room["player_ids"][0]
            room["owner_name"] = room["players"][0][1]
            _save_room(room)
            await app.send_message(
                f"房主 {leaving_name} 离开了，新房主是 {room['owner_name']}，当前{len(room['players'])}人"
            )
        else:
            room["owner_id"] = ""
            room["owner_name"] = ""
            _save_room(room)
            app.set_state("idle")
            await app.send_message("房间已解散（无人）")
    else:
        _save_room(room)
        await app.send_message(f"{leaving_name} 离开了房间，当前{len(room['players'])}人")


@app.on_command("room.waiting", ["状态", "房间状态"])
async def cmd_status(message, args: str):
    """查看房间状态"""
    room = _get_room_info()

    lines = ["🏠 房间状态:"]
    lines.append(f"状态: 等待开始")
    lines.append(f"房主: {room['owner_name']}")

    if room["players"]:
        lines.append(f"玩家列表 ({len(room['players'])}人):")
        for i, (pid, pname) in enumerate(room["players"]):
            marker = "👑" if pid == room["owner_id"] else "   "
            lines.append(f"{marker} {i+1}. {pname}")

    await app.send_message("\n".join(lines))


@app.on_command("room.waiting", ["帮助", "游戏帮助"])
async def cmd_help_room(message, args: str):
    """room状态帮助"""
    await app.send_message(
        "🎭 房间命令\n"
        "【加入】- 加入房间\n"
        "【开始】- 开始游戏（房主）\n"
        "【解散】- 解散房间（房主）\n"
        "【离开】- 离开房间\n"
        "【状态】- 查看房间状态"
    )
