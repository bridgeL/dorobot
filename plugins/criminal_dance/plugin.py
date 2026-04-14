"""犯人在跳舞插件 - 主插件"""

from dorobot import Plugin, Message, Space
from dorobot.context import get_session_id
from .card import generate_card_pool, deal_cards, Card


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
    space["group_session"] = message.session_id

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

    # ========== 处理交易子状态 ==========
    sub_state = space.get("sub_state")
    if sub_state == "trade_wait":
        # 交易等待双方选择卡牌
        trade_info = space.get("trade_info", {})
        player_idx = trade_info.get("player_idx")
        target_idx = trade_info.get("target_idx")
        initiator_card = trade_info.get("initiator_card")
        target_card = trade_info.get("target_card")

        # 检查发送者是否是交易双方，且来自私聊
        if idx != player_idx and idx != target_idx:
            return True  # 非交易玩家不响应

        # 交易响应必须在私聊中进行
        if message.session_type != "private":
            await app.send_message("⚠️ 请在私聊中回复交易！")
            return False

        # 解析玩家选择的手牌
        player_hand = hands[idx]
        selected_card = None
        selected_idx = -1
        for i, c in enumerate(player_hand):
            if c.name == content:
                selected_card = c
                selected_idx = i
                break

        if selected_card is None:
            card_names = [c.name for c in player_hand]
            await app.send_message(f"❌ 你没有「{content}」这张牌！\n你的手牌：{'、'.join(card_names)}")
            return False

        # 记录选择
        if idx == player_idx:
            trade_info["initiator_card"] = selected_card
            trade_info["initiator_idx"] = selected_idx
            await app.send_message(f"✅ 你选择了【{selected_card.name}】，等待对方选择...")
        else:
            trade_info["target_card"] = selected_card
            trade_info["target_card_idx"] = selected_idx
            await app.send_message(f"✅ 你选择了【{selected_card.name}】，等待对方选择...")

        # 检查是否双方都已选择
        initiator_card = trade_info.get("initiator_card")
        target_card = trade_info.get("target_card")

        if initiator_card and target_card:
            # 双方都选择了，执行交易
            initiator_idx = trade_info.get("player_idx")
            target_idx = trade_info.get("target_idx")
            initiator_card_idx = trade_info.get("initiator_idx")
            target_card_idx = trade_info.get("target_card_idx")

            # 从手牌移除
            initiator_hand = hands[initiator_idx]
            target_hand = hands[target_idx]
            initiator_give = initiator_hand.pop(initiator_card_idx)
            target_give = target_hand.pop(target_card_idx)

            # 交换
            initiator_hand.append(target_give)
            target_hand.append(initiator_give)

            space["hands"] = hands
            space["sub_state"] = None
            space.pop("trade_info", None)

            await app.send_message(f"🤝 交易完成！")
            await app.send_message(f"🎴 【{players[initiator_idx]['name']}】给出了【{initiator_give.name}】，获得了【{target_give.name}】")
            await app.send_message(f"🎴 【{players[target_idx]['name']}】给出了【{target_give.name}】，获得了【{initiator_give.name}】")
            await _next_turn(space)
        else:
            space["trade_info"] = trade_info
        return False

    # ========== 处理情报交换子状态 ==========
    if sub_state == "exchange_wait":
        # 情报交换等待所有玩家选择卡牌
        exchange_info = space.get("exchange_info", {})
        player_selections = exchange_info.get("player_selections", {})

        # 检查是否在等待列表中
        if idx not in exchange_info.get("waiting_list", []):
            return True  # 不在等待列表中，不响应

        # 必须在私聊中回应
        if message.session_type != "private":
            await app.send_message("⚠️ 请在私聊中选择要交换的牌！")
            return False

        # 解析玩家选择的手牌
        player_hand = hands[idx]
        selected_card = None
        selected_idx = -1
        for i, c in enumerate(player_hand):
            if c.name == content:
                selected_card = c
                selected_idx = i
                break

        if selected_card is None:
            card_names = [c.name for c in player_hand]
            await app.send_message(f"❌ 你没有「{content}」这张牌！\n你的手牌：{'、'.join(card_names)}")
            return False

        # 记录选择
        player_selections[str(idx)] = {
            "card": selected_card,
            "idx": selected_idx
        }
        exchange_info["player_selections"] = player_selections

        await app.send_message(f"✅ 你选择了【{selected_card.name}】，等待其他玩家选择...")
        space["exchange_info"] = exchange_info

        # 检查是否所有玩家都已选择
        waiting_list = exchange_info.get("waiting_list", [])
        if len(player_selections) == len(waiting_list):
            # 所有玩家都选择了，执行交换
            # 按顺时针顺序交换：每个玩家把牌给上家
            # 即：玩家 i 的牌给玩家 (i-1)
            n = len(waiting_list)
            temp_hands = [list(hands[i]) if i < len(hands) else [] for i in range(len(players))]

            for i, giver_idx in enumerate(waiting_list):
                receiver_idx = waiting_list[(i - 1 + n) % n]  # 上家（上家收牌）
                selection = player_selections[str(giver_idx)]
                given_card = selection["card"]
                given_idx = selection["idx"]
                # 从给出者手牌移除
                temp_hands[giver_idx].pop(given_idx)
                # 加入接收者手牌
                temp_hands[receiver_idx].append(given_card)

            # 更新手牌
            for i in range(len(players)):
                hands[i] = temp_hands[i]
            space["hands"] = hands

            # 生成结果消息：每个玩家收到了谁的牌
            result_parts = []
            for i, receiver_idx in enumerate(waiting_list):
                giver_idx = waiting_list[(i + 1) % n]  # 下家（下家给出）
                given_card = player_selections[str(giver_idx)]["card"]
                result_parts.append(f"{players[receiver_idx]['name']} 获得了 {players[giver_idx]['name']} 的【{given_card.name}】")

            space["sub_state"] = None
            space.pop("exchange_info", None)

            await app.send_message(f"🔄 情报交换完成！")
            await app.send_message("\n".join(result_parts))
            await _next_turn(space)

        return False

    # ========== 处理神犬子状态 ==========
    if sub_state == "dog_wait":
        dog_info = space.get("dog_info", {})
        target_idx = dog_info.get("target_idx")
        player_idx = dog_info.get("player_idx")

        # 只有被神犬指定的玩家可以响应
        if idx != target_idx:
            return True

        target_hand = hands[target_idx]
        if not target_hand:
            space["sub_state"] = None
            space.pop("dog_info", None)
            await app.send_message(f"🐕 【{players[target_idx]['name']}】没有手牌可弃！")
            await _next_turn(space)
            return False

        # 解析玩家选择的牌
        selected_card = None
        selected_idx = -1
        for i, c in enumerate(target_hand):
            if c.name == content:
                selected_card = c
                selected_idx = i
                break

        if selected_card is None:
            card_names = [c.name for c in target_hand]
            await app.send_message(f"❌ 你没有「{content}」这张牌！\n你的手牌：{'、'.join(card_names)}")
            return False

        # 执行弃牌
        discarded = target_hand.pop(selected_idx)
        space["hands"] = hands
        space["sub_state"] = None
        space.pop("dog_info", None)
        group_session = dog_info.get("group_session", message.session_id)

        if message.session_type == "private":
            # 私聊弃牌，私聊确认 + 群聊公告
            await app.send_message(f"✅ 你弃置了【{discarded.name}】")
            await app.send_message(f"🐕 【{players[target_idx]['name']}】被迫弃置：【{discarded.name}】", session_id=group_session)
        else:
            # 群聊直接弃牌
            await app.send_message(f"🐕 【{players[target_idx]['name']}】弃置了自己的【{discarded.name}】")

        if discarded.name == "犯人":
            await app.send_message(f"✅ 【{discarded.name}】被弃置！好人阵营获胜！")
            await _end_game("good", f"神犬嗅出犯人牌！")
            return

        # 目标获得神犬牌
        dog_card = dog_info.get("dog_card")
        if dog_card:
            target_hand.append(dog_card)
            space["hands"] = hands
            card_names = [c.name for c in target_hand]
            if message.session_type == "private":
                await app.send_message(f"✅ 你弃置了【{discarded.name}】，获得了【{dog_card.name}】！\n你现在的手牌：{'、'.join(card_names)}")
                await app.send_message(f"🐕 【{players[target_idx]['name']}】被迫弃置【{discarded.name}】并获得了【{dog_card.name}】", session_id=group_session)
            else:
                await app.send_message(f"🐕 【{players[target_idx]['name']}】弃置了【{discarded.name}】并获得了【{dog_card.name}】")

        await _next_turn(space)
        return False

    # 检查是否是当前出牌玩家
    turn_idx = space.get("turn", 0)
    if idx != turn_idx:
        await app.send_message(f"⚠️ 现在是 【{players[turn_idx]['name']}】 的回合，请等待。")
        return False

    # 解析卡牌名和目标（支持 "卡牌 @玩家" 或 "卡牌 玩家 牌名" 格式）
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

    # 第一发现人必须是全局第一张打出的牌
    if not space.get("first_card_played", False):
        if card_name != "第一发现人":
            await app.send_message("⚠️ 游戏第一张牌必须是「第一发现人」！")
            return False

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
        if card_name == "交易":
            await app.send_message(f"❓ 「交易」需要指定目标玩家！\n用法：交易 @玩家名\n例如：交易 玩家2\n（双方私聊各自选择要给出的牌）")
        else:
            await app.send_message(f"❓ 「{card_name}」需要指定目标玩家！\n用法：{card_name} @玩家名 或 {card_name} 玩家名")
        return False

    # 解析目标玩家索引（支持 user_id 或 user_name）
    target_idx = -1
    if target_name:
        target_idx = -1
        matches = []
        for i, p in enumerate(players):
            # user_id 精确匹配
            if p["id"] == target_name:
                matches.append(i)
            # user_name 精确匹配
            elif p["name"] == target_name:
                matches.append(i)

        if not matches:
            await app.send_message(f"❌ 未找到玩家「{target_name}」！")
            return False
        if len(matches) > 1:
            await app.send_message(f"❌ 「{target_name}」匹配到多个玩家，请使用完整名字！")
            return False
        target_idx = matches[0]

        if target_idx == idx:
            await app.send_message(f"❌ 不能以自己为目标！")
            return False

    await _play_card(idx, card_idx, card, space, target_idx, message)

    return False


async def _play_card(player_idx: int, card_idx: int, card: Card, space, target_idx: int = -1, message=None):
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
            await app.send_message(f"⚠️ 目标不是犯人！质疑失败！")

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
            # 进入神犬子状态，等待目标玩家选择弃置的牌
            space["sub_state"] = "dog_wait"
            space["dog_info"] = {
                "player_idx": player_idx,
                "target_idx": target_idx,
                "group_session": message.session_id,
                "dog_card": played_card,  # 保存神犬牌，目标可获得
            }
            await app.send_message(f"🐕 【{player['name']}】的神犬嗅探【{target['name']}】！请选择弃置的一张手牌（私聊或群聊回复牌名）")
            return  # 不切换回合，等待目标选择

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
        # 找出所有有手牌的玩家
        waiting_list = []
        for i in range(len(players)):
            if hands[i]:
                waiting_list.append(i)

        if len(waiting_list) < 2:
            await app.send_message("❌ 没有足够的玩家进行情报交换！")
            return False

        # 进入子状态，等待所有玩家选择
        space["sub_state"] = "exchange_wait"
        space["exchange_info"] = {
            "initiator_idx": player_idx,
            "waiting_list": waiting_list,
            "player_selections": {},
        }

        # 私聊通知每个有手牌的玩家
        for p_idx in waiting_list:
            p = players[p_idx]
            private_session = f"private.{p['id']}"
            hand = hands[p_idx]
            hand_str = "、".join([f"【{c.name}】" for c in hand])
            if p_idx == player_idx:
                await app.send_message(
                    f"🔄 你发起了情报交换！\n请选择要给出的牌，发送牌名即可（如：{hand[0].name}）：\n你的手牌：{hand_str}",
                    session_id=private_session,
                )
            else:
                await app.send_message(
                    f"🔄 【{player['name']}】发起了情报交换！\n请选择要给出的牌，发送牌名即可（如：{hand[0].name}）：\n你的手牌：{hand_str}",
                    session_id=private_session,
                )

        await app.send_message(f"🔄 【{player['name']}】发起了情报交换，所有玩家正在选择卡牌...")
        return False  # 不切换回合，等待所有玩家选择

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
        target_hand = hands[target_idx]
        player_hand = hands[player_idx]

        if not player_hand:
            await app.send_message(f"❌ 你没有手牌，无法交易！")
        elif not target_hand:
            await app.send_message(f"❌ 对方没有手牌，无法交易！")
        else:
            # 进入交易子状态，等待双方玩家选择要给出的牌
            space["sub_state"] = "trade_wait"
            space["trade_info"] = {
                "player_idx": player_idx,
                "target_idx": target_idx,
                "initiator_card": None,
                "target_card": None,
            }
            # 私聊通知发起人选择
            player_private_session = f"private.{player['id']}"
            player_hand_str = "、".join([f"【{c.name}】" for c in player_hand])
            await app.send_message(
                f"🤝 你向【{target['name']}】发起了交易！\n"
                f"请选择你要给出的牌，发送牌名即可（如：{player_hand[0].name}）：\n"
                f"你的手牌：{player_hand_str}",
                session_id=player_private_session,
            )
            # 私聊通知目标选择
            target_private_session = f"private.{target['id']}"
            target_hand_str = "、".join([f"【{c.name}】" for c in target_hand])
            await app.send_message(
                f"🤝 【{player['name']}】向你发起交易！\n"
                f"请选择你要给出的牌，发送牌名即可（如：{target_hand[0].name}）：\n"
                f"你的手牌：{target_hand_str}",
                session_id=target_private_session,
            )
            # 群聊只发简单提示
            await app.send_message(f"🤝 【{player['name']}】向【{target['name']}】发起了交易，双方正在选择卡牌...")
            return  # 不切换回合，等待双方选择

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

    # 关闭群聊 session 中的插件（由 Router 在消息处理结束后执行）
    # 注意：app.get_space() 对于 mounted 插件返回的是父 session 的 space，
    # 需要从私聊 session 的 space 中获取 _parent_space_ 来找到 group session
    session_id = get_session_id()
    if session_id:
        private_space = Space(app.name, session_id, memory=True)
        parent_session_id = private_space.get(f"_parent_space_{app.name}_")
        if parent_session_id:
            app.close_self(parent_session_id)


app.register()
