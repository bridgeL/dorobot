"""测试命令 - 直接导入 app 注册命令"""

from .plugin import app
from .card import generate_fixed_pool, deal_cards


@app.on_command("测试交易")
async def cmd_test_trade(message, _):
    """测试用命令：使用固定牌池快速测试交易功能

    固定牌池：
    - 玩家1: 第一发现人、交易、交易、普通人
    - 玩家2: 交易、交易、交易、交易
    - 玩家3: 神犬、交易、交易、交易
    """
    space = app.get_space()
    state = space.get("state", "room")

    if state == "game":
        await app.send_message("游戏已在进行中，请先结束当前游戏。")
        return False

    # 初始化玩家列表
    sender_id = message.sender_id
    players = [{
        "id": sender_id,
        "name": message.sender_name,
    }]

    # 添加两个测试玩家
    players.append({"id": "222", "name": "玩家2"})
    players.append({"id": "333", "name": "玩家3"})

    space["players"] = players

    # 固定牌池：每人4张，方便测试交易
    fixed_cards = [
        # 玩家1：第一发现人 + 2个交易 + 1个普通人
        "第一发现人", "交易", "交易", "普通人",
        # 玩家2：4个交易
        "交易", "交易", "交易", "交易",
        # 玩家3：神犬 + 3个交易
        "神犬", "交易", "交易", "交易",
    ]
    pool = generate_fixed_pool(fixed_cards)
    hands = deal_cards(pool, 3)

    # 保存游戏状态
    space["state"] = "game"
    space["hands"] = hands
    space["turn"] = 0
    space["first_card_played"] = False
    space["group_session"] = message.session_id

    # 确定第一回合起始玩家
    first_player_idx = 0
    for idx, hand in enumerate(hands):
        card_names = [c.name for c in hand]
        if "第一发现人" in card_names:
            first_player_idx = idx
            break
    space["turn"] = first_player_idx

    # 通知所有玩家手牌
    for i, player in enumerate(players):
        private_session = f"private.{player['id']}"
        hand = hands[i]
        hand_str = "\n".join([f"{j+1}. 【{c.name}】" for j, c in enumerate(hand)])
        await app.send_message(
            f"🃏 你的手牌：\n{hand_str}",
            session_id=private_session,
        )

    # 群聊通知
    await app.send_message(f"🎮 【测试模式】游戏开始！共 3 名玩家参与。")
    await app.send_message(f"🔔 第一回合由 【{players[first_player_idx]['name']}】 开始。")
    await app.send_message("💬 请所有玩家查看私聊消息，获取自己的手牌！")
    await app.send_message("📌 测试交易：玩家1有【第一发现人】【交易】【交易】【普通人】\n流程：1)玩家1出第一发现人 2)玩家2出一张普通牌 3)玩家3出一张普通牌 4)玩家1出交易 @玩家2")

    # 挂载插件到各玩家私聊
    for player in players:
        private_session = f"private.{player['id']}"
        await app.mount_to(private_session)

    return False


@app.on_command("测试情报交换")
async def cmd_test_exchange(message, _):
    """测试用命令：使用固定牌池快速测试情报交换功能

    固定牌池：
    - 玩家1: 第一发现人、情报交换、情报交换、普通人
    - 玩家2: 情报交换、情报交换、情报交换、情报交换
    - 玩家3: 神犬、情报交换、情报交换、情报交换
    """
    space = app.get_space()
    state = space.get("state", "room")

    if state == "game":
        await app.send_message("游戏已在进行中，请先结束当前游戏。")
        return False

    # 初始化玩家列表
    sender_id = message.sender_id
    players = [{
        "id": sender_id,
        "name": message.sender_name,
    }]

    # 添加两个测试玩家
    players.append({"id": "222", "name": "玩家2"})
    players.append({"id": "333", "name": "玩家3"})

    space["players"] = players

    # 固定牌池：每人4张，方便测试情报交换
    fixed_cards = [
        # 玩家1：第一发现人 + 普通人 + 2个情报交换
        "第一发现人", "情报交换", "情报交换", "普通人",
        # 玩家2：4个情报交换
        "情报交换", "情报交换", "情报交换", "情报交换",
        # 玩家3：神犬 + 3个情报交换
        "神犬", "情报交换", "情报交换", "情报交换",
    ]
    pool = generate_fixed_pool(fixed_cards)
    hands = deal_cards(pool, 3)

    # 保存游戏状态
    space["state"] = "game"
    space["hands"] = hands
    space["turn"] = 0
    space["first_card_played"] = False
    space["group_session"] = message.session_id

    # 确定第一回合起始玩家
    first_player_idx = 0
    for idx, hand in enumerate(hands):
        card_names = [c.name for c in hand]
        if "第一发现人" in card_names:
            first_player_idx = idx
            break
    space["turn"] = first_player_idx

    # 通知所有玩家手牌
    for i, player in enumerate(players):
        private_session = f"private.{player['id']}"
        hand = hands[i]
        hand_str = "\n".join([f"{j+1}. 【{c.name}】" for j, c in enumerate(hand)])
        await app.send_message(
            f"🃏 你的手牌：\n{hand_str}",
            session_id=private_session,
        )

    # 群聊通知
    await app.send_message(f"🎮 【测试模式】游戏开始！共 3 名玩家参与。")
    await app.send_message(f"🔔 第一回合由 【{players[first_player_idx]['name']}】 开始。")
    await app.send_message("💬 请所有玩家查看私聊消息，获取自己的手牌！")
    await app.send_message("📌 测试情报交换：当前玩家可使用「情报交换」，所有玩家顺时针交换一张牌")

    # 挂载插件到各玩家私聊
    for player in players:
        private_session = f"private.{player['id']}"
        await app.mount_to(private_session)

    return False


@app.on_command("测试谣言")
async def cmd_test_rumor(message, _):
    """测试用命令：使用固定牌池快速测试谣言功能

    固定牌池：
    - 玩家1: 第一发现人、目击者、目击者、目击者
    - 玩家2: 谣言、谣言、谣言、谣言
    - 玩家3: 普通人、普通人、普通人、普通人
    """
    space = app.get_space()
    state = space.get("state", "room")

    if state == "game":
        await app.send_message("游戏已在进行中，请先结束当前游戏。")
        return False

    # 初始化玩家列表
    sender_id = message.sender_id
    players = [{
        "id": sender_id,
        "name": message.sender_name,
    }]

    # 添加两个测试玩家
    players.append({"id": "222", "name": "玩家2"})
    players.append({"id": "333", "name": "玩家3"})

    space["players"] = players

    # 固定牌池：每人4张，方便测试谣言
    fixed_cards = [
        # 玩家1：第一发现人 + 3个目击者
        "第一发现人", "目击者", "目击者", "目击者",
        # 玩家2：4个谣言
        "谣言", "谣言", "谣言", "谣言",
        # 玩家3：4个普通人
        "普通人", "普通人", "普通人", "普通人",
    ]
    pool = generate_fixed_pool(fixed_cards)
    hands = deal_cards(pool, 3)

    # 保存游戏状态
    space["state"] = "game"
    space["hands"] = hands
    space["turn"] = 0
    space["first_card_played"] = False
    space["group_session"] = message.session_id

    # 确定第一回合起始玩家
    first_player_idx = 0
    for idx, hand in enumerate(hands):
        card_names = [c.name for c in hand]
        if "第一发现人" in card_names:
            first_player_idx = idx
            break
    space["turn"] = first_player_idx

    # 通知所有玩家手牌
    for i, player in enumerate(players):
        private_session = f"private.{player['id']}"
        hand = hands[i]
        hand_str = "\n".join([f"{j+1}. 【{c.name}】" for j, c in enumerate(hand)])
        await app.send_message(
            f"🃏 你的手牌：\n{hand_str}",
            session_id=private_session,
        )

    # 群聊通知
    await app.send_message(f"🎮 【测试模式】游戏开始！共 3 名玩家参与。")
    await app.send_message(f"🔔 第一回合由 【{players[first_player_idx]['name']}】 开始。")
    await app.send_message("💬 请所有玩家查看私聊消息，获取自己的手牌！")
    await app.send_message("📌 测试谣言：当前玩家可使用「谣言」，从下家随机抽一张牌\n玩家1:第一发现人+目击者, 玩家2:谣言, 玩家3:普通人")

    # 挂载插件到各玩家私聊
    for player in players:
        private_session = f"private.{player['id']}"
        await app.mount_to(private_session)

    return False


@app.on_command("测试侦探")
async def cmd_test_detective(message, _):
    """测试用命令：测试侦探质疑+不在场证明

    固定牌池：
    - 玩家1: 第一发现人、侦探、侦探、普通人
    - 玩家2: 犯人、不在场证明、不在场证明、普通人
    - 玩家3: 普通人、普通人、普通人、普通人
    """
    space = app.get_space()
    state = space.get("state", "room")

    if state == "game":
        await app.send_message("游戏已在进行中，请先结束当前游戏。")
        return False

    # 初始化玩家列表
    sender_id = message.sender_id
    players = [{
        "id": sender_id,
        "name": message.sender_name,
    }]
    players.append({"id": "222", "name": "玩家2"})
    players.append({"id": "333", "name": "玩家3"})

    space["players"] = players

    # 固定牌池：测试侦探+犯人+不在场证明
    fixed_cards = [
        # 玩家1：第一发现人 + 2个侦探 + 普通人
        "第一发现人", "侦探", "侦探", "普通人",
        # 玩家2：犯人 + 2个不在场证明 + 普通人
        "犯人", "不在场证明", "不在场证明", "普通人",
        # 玩家3：4个普通人
        "普通人", "普通人", "普通人", "普通人",
    ]
    pool = generate_fixed_pool(fixed_cards)
    hands = deal_cards(pool, 3)

    # 保存游戏状态
    space["state"] = "game"
    space["hands"] = hands
    space["turn"] = 0
    space["first_card_played"] = False
    space["group_session"] = message.session_id

    # 确定第一回合起始玩家
    first_player_idx = 0
    for idx, hand in enumerate(hands):
        card_names = [c.name for c in hand]
        if "第一发现人" in card_names:
            first_player_idx = idx
            break
    space["turn"] = first_player_idx

    # 通知所有玩家手牌
    for i, player in enumerate(players):
        private_session = f"private.{player['id']}"
        hand = hands[i]
        hand_str = "\n".join([f"{j+1}. 【{c.name}】" for j, c in enumerate(hand)])
        await app.send_message(
            f"🃏 你的手牌：\n{hand_str}",
            session_id=private_session,
        )

    # 群聊通知
    await app.send_message(f"🎮 【测试模式】游戏开始！共 3 名玩家参与。")
    await app.send_message(f"🔔 第一回合由 【{players[first_player_idx]['name']}】 开始。")
    await app.send_message("💬 请所有玩家查看私聊消息，获取自己的手牌！")
    await app.send_message("📌 测试侦探：玩家1有【第一发现人】【侦探】【侦探】【普通人】\n玩家2有【犯人】【不在场证明】【不在场证明】【普通人】\n测试流程：1)玩家1出第一发现人 2)玩家2出不在场证明 3)玩家1用侦探质疑玩家2")

    # 挂载插件到各玩家私聊
    for player in players:
        private_session = f"private.{player['id']}"
        await app.mount_to(private_session)

    return False


@app.on_command("测试神犬")
async def cmd_test_dog(message, _):
    """测试用命令：测试神犬效果

    固定牌池：
    - 玩家1: 第一发现人、神犬、神犬、普通人
    - 玩家2: 犯人、普通人、普通人、普通人
    - 玩家3: 普通人、普通人、普通人、普通人
    """
    space = app.get_space()
    state = space.get("state", "room")

    if state == "game":
        await app.send_message("游戏已在进行中，请先结束当前游戏。")
        return False

    sender_id = message.sender_id
    players = [{
        "id": sender_id,
        "name": message.sender_name,
    }]
    players.append({"id": "222", "name": "玩家2"})
    players.append({"id": "333", "name": "玩家3"})

    space["players"] = players

    # 固定牌池：测试神犬
    fixed_cards = [
        # 玩家1：第一发现人 + 2个神犬 + 普通人
        "第一发现人", "神犬", "神犬", "普通人",
        # 玩家2：犯人 + 3个普通人
        "犯人", "普通人", "普通人", "普通人",
        # 玩家3：4个普通人
        "普通人", "普通人", "普通人", "普通人",
    ]
    pool = generate_fixed_pool(fixed_cards)
    hands = deal_cards(pool, 3)

    space["state"] = "game"
    space["hands"] = hands
    space["turn"] = 0
    space["first_card_played"] = False

    first_player_idx = 0
    for idx, hand in enumerate(hands):
        card_names = [c.name for c in hand]
        if "第一发现人" in card_names:
            first_player_idx = idx
            break
    space["turn"] = first_player_idx

    for i, player in enumerate(players):
        private_session = f"private.{player['id']}"
        hand = hands[i]
        hand_str = "\n".join([f"{j+1}. 【{c.name}】" for j, c in enumerate(hand)])
        await app.send_message(
            f"🃏 你的手牌：\n{hand_str}",
            session_id=private_session,
        )

    await app.send_message(f"🎮 【测试模式】游戏开始！共 3 名玩家参与。")
    await app.send_message(f"🔔 第一回合由 【{players[first_player_idx]['name']}】 开始。")
    await app.send_message("💬 请所有玩家查看私聊消息，获取自己的手牌！")
    await app.send_message("📌 测试神犬：玩家1有【第一发现人】【神犬】【神犬】【普通人】，可对玩家2使用「神犬 玩家2」强制弃牌")

    for player in players:
        private_session = f"private.{player['id']}"
        await app.mount_to(private_session)

    return False
