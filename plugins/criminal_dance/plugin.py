"""犯人在跳舞插件 - 主插件"""

from dorobot import Plugin, Message
from .cards import generate_card_pool, deal_cards


app = Plugin(
    name="criminal_dance",
    layer=2,
    description="犯人在跳舞 - 多人推理桌游",
    scope="group",
    default_active=False,
)

STATE_ROOM = "room"
STATE_GAME = "game"


def _get_players(space) -> list[dict]:
    """获取房间玩家列表"""
    return space.get("players", [])


def _save_players(space, players: list[dict]):
    """保存房间玩家列表"""
    space["players"] = players


def _find_player(players: list[dict], sender_id: str) -> int:
    """查找玩家索引，不存在返回 -1"""
    for i, p in enumerate(players):
        if p["id"] == sender_id:
            return i
    return -1


@app.on_open()
async def on_open():
    """插件激活时初始化 room 状态"""
    space = app.get_space()
    space["players"] = []
    space["state"] = "room"
    await app.send_message("🎭 【犯人在跳舞】游戏已开启！\n请等待其他玩家加入...")
    await app.send_message("发送 /加入 加入房间，发送 /房间 查看当前玩家")


@app.on_close()
async def on_close():
    """插件关闭时清理"""
    space = app.get_space()
    space["players"] = []
    space["state"] = "ended"


@app.on_command("加入")
async def cmd_join(message: Message, args: str) -> bool:
    """处理 /加入 命令"""
    space = app.get_space()
    state = space.get("state", "room")

    if state != "room":
        return True  # 非 room 状态不响应

    players = _get_players(space)
    sender_id = message.sender_id

    # 检查是否已在房间
    if _find_player(players, sender_id) >= 0:
        await app.send_message("你已经在房间里了！")
        return False

    # 加入房间
    players.append({
        "id": sender_id,
        "name": message.sender_name,
    })
    _save_players(space, players)

    count = len(players)
    msg = f"✅ {message.sender_name} 加入房间！（{count}/∞）"
    if count >= 3:
        msg += "\n💡 房间人数已满足（≥3），房主可以发送 /开始 开始游戏"
    await app.send_message(msg)
    return False


@app.on_command("离开")
async def cmd_leave(message: Message, args: str) -> bool:
    """处理 /离开 命令"""
    space = app.get_space()
    state = space.get("state", "room")

    if state != "room":
        return True

    players = _get_players(space)
    sender_id = message.sender_id
    idx = _find_player(players, sender_id)

    if idx < 0:
        await app.send_message("你不在房间里！")
        return False

    player_name = players[idx]["name"]
    players.pop(idx)
    _save_players(space, players)

    if len(players) == 0:
        await app.send_message("🏠 房间已空，游戏关闭。")
        # 关闭插件（layer 2）
        session = app.get_session()
        if session:
            await session.deactivate_plugin("criminal_dance", 2)
    else:
        await app.send_message(f"👋 {player_name} 离开了房间（剩余 {len(players)} 人）")
    return False


@app.on_command("房间")
async def cmd_room(message: Message, args: str) -> bool:
    """处理 /房间 命令"""
    space = app.get_space()
    state = space.get("state", "room")

    if state != "room":
        return True

    players = _get_players(space)

    if len(players) == 0:
        await app.send_message("🏠 房间为空，还没有人加入。")
        return False

    names = [f"{i+1}. {p['name']}" for i, p in enumerate(players)]
    msg = f"🏠 【当前房间】（{len(players)} 人）\n" + "\n".join(names)
    msg += "\n\n💡 发送 /加入 加入游戏，发送 /开始 开始游戏（需≥3人）"
    await app.send_message(msg)
    return False


@app.on_command("开始")
async def cmd_start(message: Message, args: str) -> bool:
    """处理 /开始 命令"""
    space = app.get_space()
    state = space.get("state", "room")

    if state != "room":
        return True

    players = _get_players(space)
    sender_id = message.sender_id

    # 检查是否在房间
    if _find_player(players, sender_id) < 0:
        # 不在房间，先加入
        players.append({
            "id": sender_id,
            "name": message.sender_name,
        })
        _save_players(space, players)
        await app.send_message(f"✅ 你已加入房间！当前 {len(players)} 人，还需 {max(0, 3 - len(players))} 人才能开始。")
        return False

    # 已在房间，检查人数
    if len(players) < 3:
        await app.send_message(f"⚠️ 房间人数不足！当前 {len(players)} 人，需要至少 3 人才能开始游戏。")
        return False

    # 人数满足，开始游戏
    _save_players(space, players)
    space["state"] = STATE_GAME

    player_count = len(players)

    # 生成卡牌池并发牌
    pool = generate_card_pool(player_count)
    hands = deal_cards(pool, player_count)

    # 保存手牌和当前玩家
    space["hands"] = hands
    space["turn"] = 0
    space["first_card_played"] = False

    # 确定第一回合起始玩家（第一个持有第一发现人的玩家）
    first_player_idx = 0
    for idx, hand in enumerate(hands):
        card_names = [c.name for c in hand]
        if "第一发现人" in card_names:
            first_player_idx = idx
            break
    space["turn"] = first_player_idx

    # 通知所有玩家手牌（通过私聊）
    for i, player in enumerate(players):
        private_session = f"private.{player['id']}"
        hand = hands[i]
        hand_str = "\n".join([f"{j+1}. 【{c.name}】{c.description}" for j, c in enumerate(hand)])
        await app.send_message(
            f"🃏 你的手牌：\n{hand_str}",
            session_id=private_session,
        )

    # 群聊通知
    await app.send_message(f"🎮 游戏开始！共 {player_count} 名玩家参与。")
    first_player = players[first_player_idx]
    await app.send_message(f"🔔 第一回合由 【{first_player['name']}】 开始（持有第一发现人牌）。")
    await app.send_message("💬 请所有玩家查看私聊消息，获取自己的手牌！")
    return False


app.register()
