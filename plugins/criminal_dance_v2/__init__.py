"""犯罪舞蹈 V2 - 基于 AppPlugin 状态机

状态转移:
  idle -> room.waiting (创建房间)
  room.waiting -> idle (解散房间)
  room.waiting -> room.starting (开始游戏)
  room.waiting -> room.waiting (加入/离开)
  room.starting -> game.play (发牌完毕)
  game.play -> game.play (正常出牌)
  game.play -> game.trade (交易)
  game.play -> game.exchange (情报交换)
  game.play -> game.ended (游戏结束)
  game.trade -> game.play (交易完成)
  game.exchange -> game.play (情报交换完成)
  game.ended -> room.waiting (再来一局)
  game.ended -> idle (解散)
"""

from dorobot import AppPlugin, Message

# 创建 app 实例
app = AppPlugin(
    name="criminal_dance_v2",
    description="犯罪舞蹈 V2 - 狼人杀类推理社交游戏",
    scope="group",
)


# ========== 辅助函数 ==========


def _get_game():
    """获取当前游戏实例"""
    from .game import Game
    space = app.get_space()
    return space.get("game")


def _save_game(game):
    """保存游戏实例"""
    app.get_space()["game"] = game


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


async def _send_private(user_id: str, content: str):
    """发送私聊消息"""
    from dorobot.bot_manager import bot_manager
    from dorobot import ctx
    from loguru import logger

    bot_id = ctx.get_bot_id()
    if not bot_id:
        logger.warning("No bot context for private message")
        return
    bot = bot_manager.get_bot(bot_id)
    if bot and hasattr(bot, 'send_private'):
        await bot.send_private(user_id, content)
    else:
        logger.warning("Bot does not support send_private")


# ========== 生命周期 ==========


@app.on_open()
async def on_open():
    """插件启动"""
    app.set_state("idle")
    space = app.get_space()
    space["room"] = {
        "owner_id": "",
        "owner_name": "",
        "players": [],
        "player_ids": [],
    }
    space["game"] = None
    await app.send_message(
        "🎭 犯罪舞蹈 V2\n"
        "发送【创建房间】开始\n"
        "发送【帮助】查看规则"
    )


# ========== idle 状态 ==========


@app.on_command("idle", ["创建房间", "创建"])
async def cmd_create_room(message: Message, args: str):
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
async def cmd_help_idle(message: Message, args: str):
    """idle状态帮助"""
    await app.send_message(
        "🎭 犯罪舞蹈 V2\n"
        "【创建房间】- 创建新房间（房主）\n"
        "【帮助】- 查看游戏规则"
    )


# ========== room.waiting 状态 ==========


@app.on_command("room.waiting", ["加入", "加入房间"])
async def cmd_join(message: Message, args: str):
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
async def cmd_start(message: Message, args: str):
    """开始游戏"""
    room = _get_room_info()

    if message.sender_id != room["owner_id"]:
        await app.send_message("只有房主可以开始游戏")
        return

    num_players = len(room["players"])
    if num_players < 3:
        await app.send_message(f"玩家不足，需要至少3人，当前{num_players}人")
        return

    from .game import Game
    from dorobot.space import Space

    # 创建游戏实例
    game = Game()
    game.reset(num_players)
    game.plugin = app
    game.group_id = message.group_id or message.sender_id

    # 设置玩家信息
    for i, (player_id, player_name) in enumerate(room["players"]):
        game.players[i].player_id = player_id
        game.players[i].player_name = player_name

    # 建立私聊映射
    for player_id, _ in room["players"]:
        private_space = Space(app.name, f"private.{player_id}", memory=True)
        private_space["group_session_id"] = app.get_session().session_id

    _save_game(game)
    app.set_state("room.starting")

    # 启动游戏（异步发牌）
    await game.start()

    # 发牌完毕，切换到游戏状态
    app.set_state("game.play")

    # 通知当前玩家
    current = game.current_player
    await app.send_message(
        f"🎮 游戏开始！\n"
        f"公共信息: {num_players}人局\n"
        f"当前回合: {current.player_name}\n"
        f"请 {current.player_name} 发送【出牌】+ 牌名 [@目标]"
    )


@app.on_command("room.waiting", ["解散", "解散房间"])
async def cmd_dismiss(message: Message, args: str):
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
async def cmd_leave(message: Message, args: str):
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
async def cmd_status(message: Message, args: str):
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
async def cmd_help_room(message: Message, args: str):
    """room状态帮助"""
    await app.send_message(
        "🎭 房间命令\n"
        "【加入】- 加入房间\n"
        "【开始】- 开始游戏（房主）\n"
        "【解散】- 解散房间（房主）\n"
        "【离开】- 离开房间\n"
        "【状态】- 查看房间状态"
    )


# ========== game.play 状态 ==========


@app.on_command("game.play", ["出牌"])
async def cmd_play_card(message: Message, args: str):
    """出牌"""
    game = _get_game()
    if not game:
        await app.send_message("游戏未开始")
        app.set_state("idle")
        return

    if game.is_end:
        app.set_state("game.ended")
        await app.send_message("游戏已结束")
        return

    from .controller import CardPlayedMsg

    # 检查是否到它的回合
    current = game.current_player
    if not hasattr(current, "player_id") or current.player_id != message.sender_id:
        await app.send_message("还没轮到你出牌")
        return

    # 解析命令: 出牌 牌名 [@目标]
    parts = args.split()
    if not parts:
        await app.send_message("格式: 出牌 牌名 [@目标]\n例如: 出牌 情报交换\n例如: 出牌 侦探 @123456")
        return

    card_name = parts[0]

    # 查找目标
    target = None
    if len(parts) >= 2 and parts[1].startswith("@"):
        target_id = parts[1][1:]
        for p in game.players:
            if hasattr(p, "player_id") and str(p.player_id) == target_id:
                target = p
                break
        if not target:
            await app.send_message(f"未找到目标玩家: {target_id}")
            return

    # 查找手牌
    card = current.get_card(card_name)
    if not card:
        await app.send_message(f"你没有这张牌: {card_name}")
        return

    # 第一张牌必须是第一发现人
    if game.is_first:
        if card.name != "第一发现人":
            await app.send_message("第一张牌必须是【第一发现人】")
            return

    # 检查是否可以打出
    flag, reason = card.can_play(current, target)
    if not flag:
        await app.send_message(f"无法出牌: {reason}")
        return

    # 执行出牌
    current.cards.remove(card)
    await game.notify(CardPlayedMsg(current, card.name, target))
    await card.play(current, target)

    # 根据出牌类型切换状态
    from .cards.exchange_info import ExchangeInfoCard
    from .cards.trade import TradeCard

    if isinstance(card, ExchangeInfoCard):
        app.set_state("game.exchange")
    elif isinstance(card, TradeCard):
        app.set_state("game.trade")
    elif game.is_end:
        app.set_state("game.ended")
    else:
        app.set_state("game.play")


@app.on_command("game.play", ["手牌", "我的牌"])
async def cmd_handcard(message: Message, args: str):
    """查询手牌"""
    game = _get_game()
    if not game:
        await app.send_message("当前不在游戏中")
        return

    player = None
    for p in game.players:
        if hasattr(p, "player_id") and p.player_id == message.sender_id:
            player = p
            break

    if not player:
        await app.send_message("你不在游戏中")
        return

    cards_text = "\n".join(f"{i+1}. {c.name} - {c.desc}" for i, c in enumerate(player.cards))
    text = (
        f"🎴 你的手牌 ({game.num_players}人局)\n"
        f"{cards_text}\n\n"
        f"轮到你时发送: 出牌 牌名 [@目标]"
    )
    await _send_private(player.player_id, text)
    await app.send_message(f"已通过私聊发送手牌给 @{player.player_name}")


@app.on_command("game.play", ["状态", "游戏状态"])
async def cmd_game_status(message: Message, args: str):
    """查看游戏状态"""
    game = _get_game()
    if not game:
        await app.send_message("游戏未开始")
        return

    lines = ["🎮 游戏状态:"]

    current = game.current_player
    pname = current.player_name if hasattr(current, "player_name") else f"玩家{current.id}"
    lines.append(f"当前回合: {pname}")

    if game.is_first:
        lines.append("等待打出【第一发现人】")

    await app.send_message("\n".join(lines))


@app.on_command("game.play", ["结束", "结束游戏"])
async def cmd_end_game(message: Message, args: str):
    """结束游戏"""
    room = _get_room_info()
    if message.sender_id != room["owner_id"]:
        await app.send_message("只有房主可以结束游戏")
        return

    game = _get_game()
    if game:
        game.is_end = True
    app.set_state("game.ended")
    await app.send_message("游戏已结束\n发送【再来一局】重新开始\n发送【解散】解散房间")


@app.on_command("game.play", ["帮助", "游戏帮助"])
async def cmd_help_game(message: Message, args: str):
    """game状态帮助"""
    await app.send_message(
        "🎭 游戏命令\n"
        "【出牌 牌名 @目标】- 出牌\n"
        "【手牌】- 查看你的手牌（私聊）\n"
        "【状态】- 查看游戏状态\n"
        "【结束】- 结束游戏（房主）"
    )


# ========== game.exchange 状态 (情报交换) ==========


@app.on_command("game.exchange", ["出牌"])
async def cmd_exchange_play(message: Message, args: str):
    """情报交换时出牌"""
    game = _get_game()
    if not game:
        await app.send_message("游戏未开始")
        app.set_state("idle")
        return

    from .controller import ExchangeInfoController
    if not isinstance(game.controller, ExchangeInfoController):
        await app.send_message("当前不在情报交换状态")
        app.set_state("game.play")
        return

    # 解析命令
    parts = args.split()
    if not parts:
        await app.send_message("格式: 出牌 牌名")
        return

    card_name = parts[0]

    player = None
    for p in game.players:
        if hasattr(p, "player_id") and p.player_id == message.sender_id:
            player = p
            break

    if not player:
        await app.send_message("你不在游戏中")
        return

    card = player.get_card(card_name)
    if not card:
        await app.send_message(f"你没有这张牌: {card_name}")
        return

    await game.controller.handle(player, card, None)

    if isinstance(game.controller, ExchangeInfoController):
        # 还在交换中
        app.set_state("game.exchange")
    else:
        # 交换完成
        app.set_state("game.play")


@app.on_command("game.exchange", ["手牌", "我的牌"])
async def cmd_exchange_handcard(message: Message, args: str):
    """情报交换时查询手牌"""
    await cmd_handcard(message, args)


@app.on_command("game.exchange", ["帮助", "游戏帮助"])
async def cmd_help_exchange(message: Message, args: str):
    """exchange状态帮助"""
    await app.send_message(
        "🔄 情报交换状态\n"
        "请给出你要交换的牌: 出牌 牌名\n"
        "【手牌】- 查看你的手牌（私聊）"
    )


# ========== game.trade 状态 (交易) ==========


@app.on_command("game.trade", ["出牌"])
async def cmd_trade_play(message: Message, args: str):
    """交易时出牌"""
    game = _get_game()
    if not game:
        await app.send_message("游戏未开始")
        app.set_state("idle")
        return

    from .cards.trade import TradeController
    if not isinstance(game.controller, TradeController):
        await app.send_message("当前不在交易状态")
        app.set_state("game.play")
        return

    # 解析命令
    parts = args.split()
    if not parts:
        await app.send_message("格式: 出牌 牌名")
        return

    card_name = parts[0]

    player = None
    for p in game.players:
        if hasattr(p, "player_id") and p.player_id == message.sender_id:
            player = p
            break

    if not player:
        await app.send_message("你不在游戏中")
        return

    card = player.get_card(card_name)
    if not card:
        await app.send_message(f"你没有这张牌: {card_name}")
        return

    await game.controller.handle(player, card, None)

    if isinstance(game.controller, TradeController):
        app.set_state("game.trade")
    else:
        app.set_state("game.play")


@app.on_command("game.trade", ["手牌", "我的牌"])
async def cmd_trade_handcard(message: Message, args: str):
    """交易时查询手牌"""
    await cmd_handcard(message, args)


@app.on_command("game.trade", ["帮助", "游戏帮助"])
async def cmd_help_trade(message: Message, args: str):
    """trade状态帮助"""
    await app.send_message(
        "🤝 交易状态\n"
        "请给出你要交易的牌: 出牌 牌名\n"
        "【手牌】- 查看你的手牌（私聊）"
    )


# ========== game.ended 状态 ==========


@app.on_command("game.ended", ["再来一局", "再来"])
async def cmd_restart(message: Message, args: str):
    """再来一局"""
    room = _get_room_info()
    if message.sender_id != room["owner_id"]:
        await app.send_message("只有房主可以开始新游戏")
        return

    # 重置游戏
    game = _get_game()
    if game:
        from .game import Game
        num_players = game.num_players
        game.reset(num_players)
        game.plugin = app
        game.group_id = room["player_ids"][0] if room["player_ids"] else message.group_id

        for i, (player_id, player_name) in enumerate(room["players"]):
            game.players[i].player_id = player_id
            game.players[i].player_name = player_name

        _save_game(game)
        app.set_state("room.starting")
        await game.start()
        app.set_state("game.play")

        current = game.current_player
        await app.send_message(
            f"🎮 游戏重新开始！\n"
            f"当前回合: {current.player_name}\n"
            f"请 {current.player_name} 发送【出牌】+ 牌名"
        )


@app.on_command("game.ended", ["解散", "解散房间"])
async def cmd_dismiss_after_game(message: Message, args: str):
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


@app.on_command("game.ended", ["状态", "游戏状态"])
async def cmd_end_status(message: Message, args: str):
    """游戏结束状态"""
    await app.send_message(
        "🏁 游戏已结束\n"
        "【再来一局】- 重新开始（房主）\n"
        "【解散】- 解散房间（房主）"
    )


@app.on_command("game.ended", ["帮助", "游戏帮助"])
async def cmd_help_ended(message: Message, args: str):
    """ended状态帮助"""
    await app.send_message(
        "🏁 游戏结束\n"
        "【再来一局】- 重新开始（房主）\n"
        "【解散】- 解散房间（房主）"
    )


# ========== 全局命令 ==========


@app.on_command(None, ["帮助", "游戏帮助"])
async def cmd_help_global(message: Message, args: str):
    """全局帮助"""
    state = app.get_state()

    if state == "idle":
        msg = (
            "🎭 犯罪舞蹈 V2\n"
            "【创建房间】- 创建新房间\n"
            "【帮助】- 查看规则"
        )
    elif state.startswith("room"):
        msg = (
            "🎭 房间命令\n"
            "【加入】- 加入房间\n"
            "【开始】- 开始游戏（房主）\n"
            "【解散】- 解散房间（房主）\n"
            "【离开】- 离开房间\n"
            "【状态】- 查看房间状态"
        )
    elif state.startswith("game"):
        msg = (
            "🎭 游戏命令\n"
            "【出牌 牌名 @目标】- 出牌\n"
            "【手牌】- 查看手牌（私聊）\n"
            "【状态】- 查看游戏状态\n"
            "【结束】- 结束游戏（房主）"
        )
    else:
        msg = "发送【帮助】查看当前可用命令"

    await app.send_message(msg)


# ========== 游戏通知回调 ==========


async def notify_game(msg, target_player=None):
    """游戏通知回调"""
    if isinstance(msg, str):
        await app.send_message(msg)
    elif hasattr(msg, "get_data"):
        data = msg.get_data()
        msg_type = data.get("type")
        msg_content = data.get("data")

        if msg_type == "hand_card" and isinstance(msg_content, dict):
            cards = msg_content.get("cards", [])
            num_players = msg_content.get("num_players", 0)
            player_id = msg_content.get("player_id", "")

            cards_text = "\n".join(f"{i+1}. {c['name']} - {c['desc']}" for i, c in enumerate(cards))
            text = (
                f"🎴 你的手牌 ({num_players}人局)\n"
                f"{cards_text}\n\n"
                f"轮到你时发送: 出牌 牌名 [@目标]"
            )
            if player_id:
                await _send_private(player_id, text)
        elif msg_type == "text":
            await app.send_message(str(msg_content))
        else:
            await app.send_message(str(msg))
    else:
        await app.send_message(str(msg))


# 绑定通知回调
app.notify_game = notify_game

# 注册插件
app.register()
