"""犯罪舞蹈 V2 - 游戏逻辑模块"""

from loguru import logger

from dorobot import context, bot_manager

from .plugin import app
from . import room


# ========== 辅助函数 ==========


def _get_game():
    """获取当前游戏实例"""
    space = app.get_space()
    return space.get("game")


def _save_game(game):
    """保存游戏实例"""
    app.get_space()["game"] = game


async def _send_private(user_id: str, content: str):
    """发送私聊消息"""
    bot_id = context.get_bot_id()
    if not bot_id:
        logger.warning("No bot context for private message")
        return
    bot = bot_manager.get_bot(bot_id)
    if bot and hasattr(bot, "send_private"):
        await bot.send_private(user_id, content)
    else:
        logger.warning("Bot does not support send_private")


# ========== game.play 状态 ==========


@app.on_command("game.play", ["出牌"])
async def cmd_play_card(message, args: str):
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
        await app.send_message(
            "格式: 出牌 牌名 [@目标]\n例如: 出牌 情报交换\n例如: 出牌 侦探 @123456"
        )
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
async def cmd_handcard(message, args: str):
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

    cards_text = "\n".join(
        f"{i+1}. {c.name} - {c.desc}" for i, c in enumerate(player.cards)
    )
    text = (
        f"🎴 你的手牌 ({game.num_players}人局)\n"
        f"{cards_text}\n\n"
        f"轮到你时发送: 出牌 牌名 [@目标]"
    )
    await _send_private(player.player_id, text)
    await app.send_message(f"已通过私聊发送手牌给 @{player.player_name}")


@app.on_command("game.play", ["状态", "游戏状态"])
async def cmd_game_status(message, args: str):
    """查看游戏状态"""
    game = _get_game()
    if not game:
        await app.send_message("游戏未开始")
        return

    lines = ["🎮 游戏状态:"]

    current = game.current_player
    pname = (
        current.player_name if hasattr(current, "player_name") else f"玩家{current.id}"
    )
    lines.append(f"当前回合: {pname}")

    if game.is_first:
        lines.append("等待打出【第一发现人】")

    await app.send_message("\n".join(lines))


@app.on_command("game.play", ["结束", "结束游戏"])
async def cmd_end_game(message, args: str):
    """结束游戏"""
    room_data = room._get_room_info()
    if message.sender_id != room_data["owner_id"]:
        await app.send_message("只有房主可以结束游戏")
        return

    game = _get_game()
    if game:
        game.is_end = True
    app.set_state("game.ended")
    await app.send_message("游戏已结束\n发送【再来一局】重新开始\n发送【解散】解散房间")


@app.on_command("game.play", ["帮助", "游戏帮助"])
async def cmd_help_game(message, args: str):
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
async def cmd_exchange_play(message, args: str):
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
        app.set_state("game.exchange")
    else:
        app.set_state("game.play")


@app.on_command("game.exchange", ["手牌", "我的牌"])
async def cmd_exchange_handcard(message, args: str):
    """情报交换时查询手牌"""
    await cmd_handcard(message, args)


@app.on_command("game.exchange", ["帮助", "游戏帮助"])
async def cmd_help_exchange(message, args: str):
    """exchange状态帮助"""
    await app.send_message(
        "🔄 情报交换状态\n"
        "请给出你要交换的牌: 出牌 牌名\n"
        "【手牌】- 查看你的手牌（私聊）"
    )


# ========== game.trade 状态 (交易) ==========


@app.on_command("game.trade", ["出牌"])
async def cmd_trade_play(message, args: str):
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
async def cmd_trade_handcard(message, args: str):
    """交易时查询手牌"""
    await cmd_handcard(message, args)


@app.on_command("game.trade", ["帮助", "游戏帮助"])
async def cmd_help_trade(message, args: str):
    """trade状态帮助"""
    await app.send_message(
        "🤝 交易状态\n"
        "请给出你要交易的牌: 出牌 牌名\n"
        "【手牌】- 查看你的手牌（私聊）"
    )


# ========== game.ended 状态 ==========


@app.on_command("game.ended", ["再来一局", "再来"])
async def cmd_restart(message, args: str):
    """再来一局"""
    room_data = room._get_room_info()
    if message.sender_id != room_data["owner_id"]:
        await app.send_message("只有房主可以开始新游戏")
        return

    # 重置游戏
    game_core = _get_game()
    if game_core:
        from .game_core import Game

        num_players = game_core.num_players
        game_core.reset(num_players)
        game_core.plugin = app
        game_core.group_id = (
            room_data["player_ids"][0] if room_data["player_ids"] else message.group_id
        )

        for i, (player_id, player_name) in enumerate(room_data["players"]):
            game_core.players[i].player_id = player_id
            game_core.players[i].player_name = player_name

        _save_game(game_core)
        app.set_state("room.starting")
        await game_core.start()
        app.set_state("game.play")

        current = game_core.current_player
        await app.send_message(
            f"🎮 游戏重新开始！\n"
            f"当前回合: {current.player_name}\n"
            f"请 {current.player_name} 发送【出牌】+ 牌名"
        )


@app.on_command("game.ended", ["解散", "解散房间"])
async def cmd_dismiss_after_game(message, args: str):
    """解散房间"""
    room_data = room._get_room_info()
    if message.sender_id != room_data["owner_id"]:
        await app.send_message("只有房主可以解散房间")
        return

    room_data["owner_id"] = ""
    room_data["owner_name"] = ""
    room_data["players"] = []
    room_data["player_ids"] = []
    room._save_room(room_data)
    _save_game(None)
    app.set_state("idle")

    await app.send_message("房间已解散")


@app.on_command("game.ended", ["状态", "游戏状态"])
async def cmd_end_status(message, args: str):
    """游戏结束状态"""
    await app.send_message(
        "🏁 游戏已结束\n"
        "【再来一局】- 重新开始（房主）\n"
        "【解散】- 解散房间（房主）"
    )


@app.on_command("game.ended", ["帮助", "游戏帮助"])
async def cmd_help_ended(message, args: str):
    """ended状态帮助"""
    await app.send_message(
        "🏁 游戏结束\n" "【再来一局】- 重新开始（房主）\n" "【解散】- 解散房间（房主）"
    )


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

            cards_text = "\n".join(
                f"{i+1}. {c['name']} - {c['desc']}" for i, c in enumerate(cards)
            )
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
