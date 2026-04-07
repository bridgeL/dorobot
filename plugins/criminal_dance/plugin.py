"""犯罪舞蹈 - 狼人杀类推理社交游戏

游戏流程:
1. 有人创建房间，等待玩家加入
2. 玩家发送"加入"加入房间
3. 房主发送"开始"启动游戏
4. 玩家轮流出牌，使用"出牌 + 牌名 + @目标"格式
5. 游戏结束后房间保留，可由房主开始下一局或解散
"""

from typing import Optional

from dorobot import Plugin, Message, Space
from .controller import CardPlayedMsg


class CriminalDancePlugin(Plugin):
    """犯罪舞蹈游戏插件"""

    def __init__(
        self,
        name: str = "criminal_dance",
        layer: int = 2,
        description: str = "犯罪舞蹈 - 狼人杀类推理社交游戏",
        bots: list = None,
        scope: str = "group",
        default_active: bool = True,
    ):
        super().__init__(
            name=name,
            layer=layer,
            description=description,
            bots=bots,
            scope=scope,
            default_active=default_active,
        )
        pass  # 保留用于未来异步输入

    def _get_space(self, group_id: str) -> Space:
        """获取群聊对应的Space，用于存储房间和游戏数据"""
        return Space("criminal_dance", group_id, memory=True)

    def _get_room(self, group_id: str) -> Optional[dict]:
        """获取房间信息"""
        space = self._get_space(group_id)
        return space.get("room")

    def _save_room(self, group_id: str, room: dict):
        """保存房间信息"""
        space = self._get_space(group_id)
        space["room"] = room

    async def handle_message(self, message: Message) -> bool:
        """处理消息"""
        session = self.get_session()
        if not session:
            return True

        group_id = session.group_id or message.sender_id
        content = message.content.strip()

        # 获取房间状态
        room = self._get_room(group_id)

        # 解析命令
        if content == "创建房间":
            return await self._cmd_create_room(message, group_id)
        elif content == "加入":
            return await self._cmd_join(message, group_id, room)
        elif content == "开始" or content == "开始游戏":
            return await self._cmd_start(message, group_id, room)
        elif content == "解散" or content == "解散房间":
            return await self._cmd_dismiss(message, group_id, room)
        elif content == "状态" or content == "房间状态":
            return await self._cmd_status(message, group_id, room)
        elif content.startswith("出牌"):
            return await self._cmd_play_card(message, group_id, room)
        elif content == "离开":
            return await self._cmd_leave(message, group_id, room)
        elif content == "帮助" or content == "游戏帮助":
            return await self._cmd_help(message)

        return True

    async def _cmd_create_room(self, message: Message, group_id: str) -> bool:
        """创建房间"""
        existing = self._get_room(group_id)
        if existing:
            await self.send_message("房间已存在，请先解散或加入现有房间")
            return False

        room = {
            "status": "waiting",  # waiting, playing, ended
            "owner_id": message.sender_id,
            "owner_name": message.sender_name,
            "players": [(message.sender_id, message.sender_name)],  # 房主也在列表中
            "player_ids": [message.sender_id],
            "game": None,
        }
        self._save_room(group_id, room)

        msg = (
            f"🎭 犯罪舞蹈房间已创建！\n"
            f"房主: {message.sender_name}\n"
            f"等待玩家加入...\n"
            f"发送【加入】入座\n"
            f"发送【状态】查看房间\n"
            f"发送【解散】解散房间"
        )
        await self.send_message(msg)
        return False

    async def _cmd_join(self, message: Message, group_id: str, room: dict) -> bool:
        """加入房间"""
        if not room:
            await self.send_message("房间不存在，请先创建房间")
            return False

        if room["status"] != "waiting":
            await self.send_message("游戏已开始或已结束，无法加入")
            return False

        if message.sender_id in room["player_ids"]:
            await self.send_message("你已经在房间里了")
            return False

        # 加入房间
        room["players"].append((message.sender_id, message.sender_name))
        room["player_ids"].append(message.sender_id)
        self._save_room(group_id, room)

        player_count = len(room["players"])
        msg = (
            f"✅ {message.sender_name} 加入了房间！\n"
            f"当前玩家: {player_count}人"
        )
        if player_count >= 3:
            msg += f"\n人数已够，房主可以发送【开始】开始游戏"
        else:
            msg += f"\n等待更多玩家加入...（需要至少3人）"

        await self.send_message(msg)
        return False

    async def _cmd_leave(self, message: Message, group_id: str, room: dict) -> bool:
        """离开房间"""
        if not room:
            await self.send_message("房间不存在")
            return False

        if room["status"] != "waiting":
            await self.send_message("游戏已开始，无法离开")
            return False

        if message.sender_id not in room["player_ids"]:
            await self.send_message("你不在房间里")
            return False

        # 如果是房主
        if message.sender_id == room["owner_id"]:
            if len(room["players"]) <= 1:
                # 只有房主一个人，直接解散
                self._save_room(group_id, None)
                await self.send_message("房主离开了房间，房间已解散")
            else:
                # 转移房主给下一个玩家
                idx = room["player_ids"].index(message.sender_id)
                room["players"].pop(idx)
                room["player_ids"].pop(idx)
                room["owner_id"] = room["player_ids"][0]
                room["owner_name"] = room["players"][0][1]
                self._save_room(group_id, room)
                await self.send_message(f"房主离开了，新房主是 {room['owner_name']}")
        else:
            idx = room["player_ids"].index(message.sender_id)
            room["players"].pop(idx)
            room["player_ids"].pop(idx)
            self._save_room(group_id, room)
            await self.send_message(f"{message.sender_name} 离开了房间，当前{len(room['players'])}人")

        return False

    async def _cmd_start(self, message: Message, group_id: str, room: dict) -> bool:
        """开始游戏"""
        if not room:
            await self.send_message("房间不存在")
            return False

        if room["status"] != "waiting":
            await self.send_message("游戏已经开始或已结束")
            return False

        if message.sender_id != room["owner_id"]:
            await self.send_message("只有房主可以开始游戏")
            return False

        num_players = len(room["players"])
        if num_players < 3:
            await self.send_message(f"玩家不足，需要至少3人，当前{num_players}人")
            return False

        # 创建游戏实例
        from .game import Game

        game = Game()
        game.reset(num_players)
        game.plugin = self
        game.group_id = group_id

        # 设置玩家信息
        for i, (player_id, player_name) in enumerate(room["players"]):
            game.players[i].player_id = player_id
            game.players[i].player_name = player_name

        room["game"] = game
        room["status"] = "playing"
        self._save_room(group_id, room)

        # 启动游戏
        await game.start()

        return False

    async def _cmd_dismiss(self, message: Message, group_id: str, room: dict) -> bool:
        """解散房间"""
        if not room:
            await self.send_message("房间不存在")
            return False

        if message.sender_id != room["owner_id"]:
            await self.send_message("只有房主可以解散房间")
            return False

        self._save_room(group_id, None)
        await self.send_message("房间已解散")
        return False

    async def _cmd_status(self, message: Message, group_id: str, room: dict) -> bool:
        """查看房间状态"""
        if not room:
            await self.send_message("房间不存在")
            return False

        lines = ["🏠 房间状态:"]

        status_text = {"waiting": "等待开始", "playing": "游戏中", "ended": "已结束"}
        lines.append(f"状态: {status_text.get(room['status'], '未知')}")
        lines.append(f"房主: {room['owner_name']}")

        if room["players"]:
            lines.append(f"玩家列表 ({len(room['players'])}人):")
            for i, (pid, pname) in enumerate(room["players"]):
                marker = "👑" if pid == room["owner_id"] else "  "
                marker += "🎮" if pid == room.get("current_player_id") else "   "
                lines.append(f"{marker} {i+1}. {pname}")

        if room["status"] == "playing" and room.get("game"):
            game = room["game"]
            pname = game.current_player.player_name if hasattr(game.current_player, 'player_name') else f"玩家{game.current_player.id}"
            lines.append(f"\n当前回合: {pname}")
            lines.append(f"公共信息: {game.num_players}人局")

        await self.send_message("\n".join(lines))
        return False

    async def _cmd_play_card(self, message: Message, group_id: str, room: dict) -> bool:
        """出牌"""
        if not room or room["status"] != "playing":
            await self.send_message("游戏未开始")
            return False

        game = room["game"]
        if not game:
            await self.send_message("游戏数据异常")
            return False

        # 找到当前玩家
        current_player = game.current_player
        if not hasattr(current_player, "player_id") or current_player.player_id != message.sender_id:
            await self.send_message("还没轮到你出牌")
            return False

        # 解析出牌命令
        content = message.content.strip()
        # 格式: 出牌 牌名 @目标ID 或 出牌 牌名
        parts = content.split()
        if len(parts) < 2:
            await self.send_message("格式错误，请使用: 出牌 牌名 [@目标]")
            return False

        card_name = parts[1]

        # 查找目标
        target = None
        if len(parts) >= 3 and parts[2].startswith("@"):
            target_id = parts[2][1:]
            for p in game.players:
                if hasattr(p, "player_id") and str(p.player_id) == target_id:
                    target = p
                    break
            if not target:
                await self.send_message(f"未找到目标玩家: {target_id}")
                return False

        # 查找手牌
        card = current_player.get_card(card_name)
        if not card:
            await self.send_message(f"你没有这张牌: {card_name}")
            return False

        # 检查是否可以打出
        flag, reason = card.can_play(current_player, target)
        if not flag:
            await self.send_message(f"无法出牌: {reason}")
            return False

        # 执行出牌
        current_player.cards.remove(card)
        await game.notify(CardPlayedMsg(current_player, card.name, target))
        await card.play(current_player, target)

        if game.is_end:
            # 游戏结束
            room["status"] = "ended"
            self._save_room(group_id, room)
        elif type(game.controller).__name__ == "PlayCardController":
            # 正常出牌，切换到下一个玩家
            await game.next_turn()

        return False

    async def _cmd_help(self, message: Message) -> bool:
        """显示帮助"""
        help_text = """
🎭 犯罪舞蹈游戏帮助

【房间命令】
  创建房间 - 创建新房间（房主）
  加入 - 加入房间
  离开 - 离开房间
  开始 - 开始游戏（房主）
  解散 - 解散房间（房主）
  状态 - 查看房间状态

【游戏命令】
  出牌 牌名 [@目标] - 出牌
  例: 出牌 情报交换
  例: 出牌 侦探 @123456

【游戏规则】
  3-8人游戏，每局有犯人、侦探等身份
  通过出牌找出犯人或隐藏身份
  手牌数量达到限制时必须出牌

【牌型说明】
  第一发现人: 必须第一张打出
  犯人: 最后手牌，打出即获胜（被抓则失败）
  侦探: ≤2张手牌时可出，质疑玩家
  警部: ≤2张手牌时可出，监视玩家
  目击者: 查看其他玩家手牌
  交易: 与玩家交换一张手牌
  情报交换: 所有玩家交换上家手牌
  谣言: 随机抽下家一张手牌
  神犬: 目标弃牌，可抓到犯人
  不在场证明: 防止被质疑
  共犯: 加入坏人阵营
"""
        await self.send_message(help_text.strip())
        return False

    # ==================== 游戏通知回调 ====================

    async def _send_private(self, user_id: str, content: str):
        """发送私聊消息给指定用户"""
        from dorobot.bot_manager import bot_manager
        bot_id = ctx.get_bot_id()
        if not bot_id:
            logger.warning(f"Plugin {self.name} has no bot context, cannot send private message")
            return
        bot = bot_manager.get_bot(bot_id)
        if bot and hasattr(bot, 'send_private'):
            await bot.send_private(user_id, content)
        else:
            # Fallback to group message if send_private not available
            logger.warning(f"Bot {bot_id} does not support send_private, falling back to group message")
            await self.send_message(content)

    async def notify_game(self, msg, target_player=None):
        """游戏通知回调"""
        session = self.get_session()
        if not session:
            return

        if isinstance(msg, str):
            await self.send_message(msg)
        elif hasattr(msg, "get_data"):
            data = msg.get_data()
            msg_type = data.get("type")
            msg_content = data.get("data")

            if msg_type == "hand_card" and isinstance(msg_content, dict):
                # 私聊手牌
                cards = msg_content.get("cards", [])
                num_players = msg_content.get("num_players", 0)

                # 通过 target_player 获取玩家名字和ID
                player_name = target_player.player_name if target_player else "未知玩家"
                player_id = target_player.player_id if target_player else ""

                cards_text = "\n".join(f"{i+1}. {c['name']} - {c['desc']}" for i, c in enumerate(cards))
                text = (
                    f"🎴 你的手牌 ({num_players}人局)\n"
                    f"{cards_text}\n\n"
                    f"轮到你时发送: 出牌 牌名 [@目标]"
                )
                # 发送私聊消息
                await self._send_private(player_id, text)
            elif msg_type == "text":
                await self.send_message(str(msg_content))
            else:
                await self.send_message(str(msg))
        else:
            await self.send_message(str(msg))


# 注册插件
plugin_instance = CriminalDancePlugin()
from dorobot.plugin_manager import plugin_manager
plugin_manager.register(
    "criminal_dance",
    plugin_instance,
    active=True
)
