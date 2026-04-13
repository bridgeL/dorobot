"""犯人在跳舞插件 - 主插件"""

from dorobot import Plugin, Message
from .cards import generate_card_pool, deal_cards, Card


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

    # 检查房间是否已满
    if len(players) >= 8:
        await app.send_message("⚠️ 房间已满（8人），无法再加入！")
        return False

    # 加入房间
    players.append({
        "id": sender_id,
        "name": message.sender_name,
    })
    _save_players(space, players)

    count = len(players)
    msg = f"✅ {message.sender_name} 加入房间！（{count}/8）"
    if count >= 3:
        msg += "\n💡 房间人数已满足（≥3），房主可以发送 /开始 开始游戏"
    if count == 8:
        msg += "\n⚠️ 房间已满！房主可以发送 /开始 开始游戏"
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
    msg = f"🏠 【当前房间】（{len(players)}/8 人）\n" + "\n".join(names)
    if len(players) >= 8:
        msg += "\n\n⚠️ 房间已满！房主可以发送 /开始 开始游戏"
    else:
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

    # 将插件挂载到每个玩家的私聊 session（layer 1），便于 /手牌 命令使用
    for player in players:
        private_session = f"private.{player['id']}"
        await app.mount_to(private_session)

    return False


# ==================== 帮助命令 ====================

@app.on_command("帮助")
async def cmd_help(message: Message, args: str) -> bool:
    """处理 /帮助 命令（room 和 game 状态均可使用）"""
    help_text = """🎭 【犯人在跳舞】游戏帮助

📋 【房间命令】（游戏开启前）
  /加入  - 加入房间
  /离开  - 离开房间
  /房间  - 查看当前房间状态
  /开始  - 开始游戏（需≥3人）
  /帮助  - 显示本帮助

📋 【游戏命令】（游戏开始后）
  /手牌  - 私聊查看自己的手牌
  /状态  - 查看当前游戏状态
  /帮助  - 显示本帮助

📜 【卡牌说明】
  【第一发现人】必须第一张打出
  【犯人】手牌≤1时可打出
  【侦探】手牌≤2时可打出，质疑目标
  【警部】手牌≤2时可打出，监视目标
  【神犬】指定目标弃一张牌
  【不在场证明】被动防质疑
  【共犯】打出后加入坏人阵营
  【目击者】查看目标手牌
  【谣言】【情报交换】【交易】

⚖️ 【胜负规则】
  好人：抓到此局犯人即获胜
  坏人：打出犯人并成功逃脱即获胜
"""
    await app.send_message(help_text)
    return False


# ==================== game 状态命令 ====================

@app.on_command("手牌")
async def cmd_hand(message: Message, args: str) -> bool:
    """处理 /手牌 命令（私聊查看手牌）"""
    space = app.get_space()
    if space.get("state") != STATE_GAME:
        return True

    sender_id = message.sender_id
    players = _get_players(space)
    hands = space.get("hands", [])

    idx = _find_player(players, sender_id)
    if idx < 0:
        return True  # 不在游戏中不响应

    hand = hands[idx]
    if not hand:
        await app.send_message("你已经没有手牌了！")
    else:
        hand_str = "\n".join([f"{j+1}. 【{c.name}】{c.description}" for j, c in enumerate(hand)])
        await app.send_message(f"🃏 你的手牌：\n{hand_str}")
    return False


@app.on_command("状态")
async def cmd_status(message: Message, args: str) -> bool:
    """处理 /状态 命令（群聊查看游戏状态）"""
    space = app.get_space()
    if space.get("state") != STATE_GAME:
        return True

    players = _get_players(space)
    hands = space.get("hands", [])
    turn_idx = space.get("turn", 0)

    lines = ["📊 【游戏状态】"]
    for i, player in enumerate(players):
        hand_count = len(hands[i]) if i < len(hands) else 0
        marker = " ◀" if i == turn_idx else ""
        lines.append(f"{i+1}. {player['name']}（{hand_count}张手牌）{marker}")

    current = players[turn_idx] if turn_idx < len(players) else {}
    lines.append(f"\n🔔 当前出牌：{current.get('name', '未知')}")
    await app.send_message("\n".join(lines))
    return False


@app.on_message()
async def handle_game_message(message: Message) -> bool:
    """处理游戏中的卡牌消息（私聊或群聊直接发送卡牌名）"""
    space = app.get_space()
    if space.get("state") != STATE_GAME:
        return True

    # 忽略命令前缀的消息
    content = message.content.strip()
    if content.startswith("/"):
        return True

    sender_id = message.sender_id
    players = _get_players(space)
    hands = space.get("hands", [])

    idx = _find_player(players, sender_id)
    if idx < 0:
        return True  # 不在游戏中

    # 检查是否是当前出牌玩家
    turn_idx = space.get("turn", 0)
    if idx != turn_idx:
        await app.send_message(f"⚠️ 现在是 【{players[turn_idx]['name']}】 的回合，请等待。")
        return False

    # 解析卡牌名和目标（支持 "卡牌 @玩家" 或 "卡牌 玩家" 格式）
    parts = content.split()
    card_name = parts[0]
    target_name = None
    if len(parts) > 1:
        # 去除可能的 @ 符号
        target_name = parts[1].lstrip("@")

    # 查找手牌
    if idx >= len(hands):
        return False

    card = None
    card_idx = -1
    for i, c in enumerate(hands[idx]):
        if c.name == card_name:
            card = c
            card_idx = i
            break

    if card is None:
        await app.send_message(f"❌ 你没有「{card_name}」这张牌！")
        return False

    # 检查手牌数量限制（必须在 pop 之前检查）
    hand_count = len(hands[idx])
    if card_name == "犯人" and hand_count > 1:
        await app.send_message(f"❌ 「犯人」只能在手牌≤1时打出！你当前有 {hand_count} 张手牌。")
        return False
    if card_name == "侦探" and hand_count > 2:
        await app.send_message(f"❌ 「侦探」只能在手牌≤2时打出！你当前有 {hand_count} 张手牌。")
        return False
    if card_name == "警部" and hand_count > 2:
        await app.send_message(f"❌ 「警部」只能在手牌≤2时打出！你当前有 {hand_count} 张手牌。")
        return False

    # 需要指定目标但没有提供
    need_target = card_name in ["侦探", "警部", "神犬", "目击者", "交易"]
    if need_target and not target_name:
        await app.send_message(f"❓ 「{card_name}」需要指定目标玩家！\n用法：{card_name} @玩家名 或 {card_name} 玩家名")
        return False

    # 解析目标玩家索引
    target_idx = -1
    if target_name:
        for i, p in enumerate(players):
            if target_name in p["name"] or p["id"] == target_name:
                target_idx = i
                break
        if target_idx < 0:
            await app.send_message(f"❌ 未找到玩家「{target_name}」！")
            return False
        if target_idx == idx:
            await app.send_message(f"❌ 不能以自己为目标！")
            return False

    # ========== 执行卡牌效果 ==========
    await _play_card(idx, card_idx, card, space, target_idx)

    return False


async def _play_card(player_idx: int, card_idx: int, card: Card, space, target_idx: int = -1):
    """执行卡牌效果

    Args:
        player_idx: 出牌玩家索引
        card_idx: 手牌索引
        card: 卡牌对象
        space: 游戏空间
        target_idx: 目标玩家索引（需要目标时）
    """
    import random

    players = _get_players(space)
    hands = space.get("hands", [])
    player = players[player_idx]

    # 从手牌中移除这张牌
    played_card = hands[player_idx].pop(card_idx)
    space["hands"] = hands

    card_name = played_card.name

    # 通用通知
    await app.send_message(f"【{player['name']}】打出了 【{card_name}】。")

    # ========== 第一发现人 ==========
    if card_name == "第一发现人":
        if space.get("first_card_played", False):
            await app.send_message("⚠️ 第一发现人已经打出过，本牌无效果。")
        else:
            space["first_card_played"] = True
            await app.send_message("✅ 第一发现人打出，游戏正式开始！")

    # ========== 普通人 ==========
    elif card_name == "普通人":
        await app.send_message("这张牌没有任何效果。")

    # ========== 共犯 ==========
    elif card_name == "共犯":
        space.setdefault("bad_players", [])
        if player_idx not in space["bad_players"]:
            space["bad_players"].append(player_idx)
        await app.send_message(f"⚠️ 【{player['name']}】宣布自己是共犯！已加入坏人阵营！")

    # ========== 不在场证明 ==========
    elif card_name == "不在场证明":
        space.setdefault("alibi_players", [])
        if player_idx not in space["alibi_players"]:
            space["alibi_players"].append(player_idx)
        await app.send_message(f"【{player['name']}】声明自己不在场证明。")

    # ========== 犯人 ==========
    elif card_name == "犯人":
        bad_players = space.get("bad_players", [])
        if player_idx in bad_players:
            await app.send_message(f"🚨 【{player['name']}】打出了犯人牌！坏人阵营获胜！")
            await _end_game("bad", f"【{player['name']}】是犯人，坏人逃脱！")
        else:
            await app.send_message(f"🚨 【{player['name']}】打出了犯人牌！好人阵营获胜！")
            await _end_game("good", f"【{player['name']}】打出犯人牌被抓！")
        return

    # ========== 侦探 ==========
    elif card_name == "侦探":
        target = players[target_idx]
        target_hand = hands[target_idx]
        alibi_players = space.get("alibi_players", [])

        # 检查目标是否有犯人且无不在场证明
        has_criminal = any(c.name == "犯人" for c in target_hand)
        has_alibi = target_idx in alibi_players

        if has_criminal and not has_alibi:
            await app.send_message(f"🕵️ 【{player['name']}】质疑【{target['name']}】！")
            await app.send_message(f"✅ 目标确实持有犯人牌且无不在场证明！好人阵营获胜！")
            await _end_game("good", f"侦探质疑成功：【{target['name']}】持有犯人牌！")
            return
        else:
            await app.send_message(f"🕵️ 【{player['name']}】质疑【{target['name']}】！")
            if has_criminal and has_alibi:
                await app.send_message(f"⚠️ 目标有犯人牌但有不在场证明！质疑失败！")
            else:
                await app.send_message(f"⚠️ 目标没有犯人牌！质疑失败！")

    # ========== 警部 ==========
    elif card_name == "警部":
        target = players[target_idx]
        # 记录警部指定的目标
        space["policiamento_target"] = target_idx
        await app.send_message(f"👮 【{player['name']}】指定【{target['name']}】为重点监视对象！")

    # ========== 神犬 ==========
    elif card_name == "神犬":
        target = players[target_idx]
        target_hand = hands[target_idx]

        if not target_hand:
            await app.send_message(f"🐕 【{target['name']}】没有手牌可弃！")
        else:
            # 随机弃一张牌
            discard_idx = random.randint(0, len(target_hand) - 1)
            discarded = target_hand.pop(discard_idx)
            await app.send_message(f"🐕 【{player['name']}】的神犬嗅探【{target['name']}】！")
            await app.send_message(f"🎴 【{target['name']}】被迫弃置：【{discarded.name}】")

            if discarded.name == "犯人":
                await app.send_message(f"✅ 【{discarded.name}】被弃置！好人阵营获胜！")
                await _end_game("good", f"神犬嗅出犯人牌！")
                return

    # ========== 谣言 ==========
    elif card_name == "谣言":
        await app.send_message("📢 谣言四起！所有玩家从下家随机抽取一张手牌...")
        rumor_results = []
        for i in range(len(players)):
            if not hands[i]:
                continue
            next_idx = (i + 1) % len(players)
            if not hands[next_idx]:
                continue
            # 从下家随机抽一张
            rand_idx = random.randint(0, len(hands[next_idx]) - 1)
            stolen_card = hands[next_idx].pop(rand_idx)
            hands[i].append(stolen_card)
            rumor_results.append(f"{players[i]['name']} 从 {players[next_idx]['name']} 抽到了【{stolen_card.name}】")

        if rumor_results:
            await app.send_message("\n".join(rumor_results))
        else:
            await app.send_message("没有可抽取的牌！")
        space["hands"] = hands

    # ========== 情报交换 ==========
    elif card_name == "情报交换":
        await app.send_message("🔄 情报交换！所有玩家将一张牌传给上家...")
        exchange_results = []
        temp_cards = []

        # 先收集每人的第一张牌
        for i in range(len(players)):
            if hands[i]:
                temp_cards.append(hands[i][0])
            else:
                temp_cards.append(None)

        # 然后把上家的牌发下去
        for i in range(len(players)):
            prev_idx = (i - 1 + len(players)) % len(players)
            if hands[i] and temp_cards[prev_idx]:
                hands[i].pop(0)
                hands[i].append(temp_cards[prev_idx])
                if temp_cards[prev_idx]:
                    exchange_results.append(f"{players[i]['name']} 收到了来自 {players[prev_idx]['name']} 的【{temp_cards[prev_idx].name}】")

        if exchange_results:
            await app.send_message("\n".join(exchange_results))
        else:
            await app.send_message("没有可交换的牌！")
        space["hands"] = hands

    # ========== 目击者 ==========
    elif card_name == "目击者":
        target = players[target_idx]
        target_hand = hands[target_idx]

        await app.send_message(f"👁️ 【{player['name']}】目击了【{target['name']}】的手牌！")
        if target_hand:
            cards_str = "、".join([f"【{c.name}】" for c in target_hand])
            await app.send_message(f"🎴 【{target['name']}】的手牌：{cards_str}")
        else:
            await app.send_message(f"🎴 【{target['name']}】没有手牌！")

    # ========== 交易 ==========
    elif card_name == "交易":
        target = players[target_idx]
        player_hand = hands[player_idx]
        target_hand = hands[target_idx]

        if not player_hand:
            await app.send_message(f"❌ 你没有手牌，无法交易！")
        elif not target_hand:
            await app.send_message(f"❌ 对方没有手牌，无法交易！")
        else:
            # 各给一张对方
            player_card = player_hand[0]
            target_card = target_hand[0]
            player_hand.pop(0)
            target_hand.pop(0)
            player_hand.append(target_card)
            target_hand.append(player_card)
            await app.send_message(f"🤝 【{player['name']}】与【{target['name']}】交易成功！")
            await app.send_message(f"🎴 你给出了【{player_card.name}】，获得了【{target_card.name}】")
            space["hands"] = hands

    # ========== 其他人 ==========
    else:
        await app.send_message(f"【{card_name}】的效果尚未实现。")

    # 切换到下一个玩家
    await _next_turn(space)


async def _next_turn(space):
    """切换到下一个有手牌的玩家"""
    players = _get_players(space)
    hands = space.get("hands", [])

    tried = 0
    turn = space.get("turn", 0)
    while tried < len(players):
        turn = (turn + 1) % len(players)
        tried += 1
        if hands[turn]:  # 有手牌
            break

    space["turn"] = turn
    current = players[turn]
    await app.send_message(f"🔔 轮到 【{current['name']}】 出牌。")


async def _end_game(winner: str, reason: str):
    """结束游戏"""
    space = app.get_space()
    space["state"] = "ended"
    space["winner"] = winner
    space["reason"] = reason

    if winner == "bad":
        await app.send_message(f"🚨 游戏结束！坏人阵营获胜！\n原因：{reason}")
    else:
        await app.send_message(f"🕵️ 游戏结束！好人阵营获胜！\n原因：{reason}")

    # 从所有私聊 session 卸载插件
    app.unmount_from_all()

    # 关闭插件
    session = app.get_session()
    if session:
        await session.deactivate_plugin("criminal_dance", 2)


app.register()
