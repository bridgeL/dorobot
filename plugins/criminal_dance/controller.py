from typing import TYPE_CHECKING, Optional
from .card import Card
from .msg import Msg
from .player import Player

if TYPE_CHECKING:
    from .game import Game


class Controller:
    def __init__(self, game: "Game"):
        self.game = game

    async def handle(self, player: Player, card: Card, target: Optional[Player]) -> bool:
        raise NotImplementedError


class PlayCardController(Controller):
    async def handle(self, player, card, target):
        game = self.game

        # 检查是否到它的回合
        if player.id != game.players[game.current_player_index].id:
            await self.game.notify(NotYourTurnMsg())
            return False

        # 第一张牌必须是第一发现人
        if self.game.is_first:
            from .cards.first import FirstCard

            if card.name != FirstCard.name:
                await self.game.notify(MustFirstMsg())
                return False

        # 检查是否可以打出这张牌
        flag, reason = card.can_play(player, target)
        if not flag:
            await self.game.notify(CannotPlayCardMsg(player, card, reason))
            return False

        # 从手牌中移除这张牌并打出
        player.cards.remove(card)

        # 打出牌并通知
        await self.game.notify(CardPlayedMsg(player, card.name, target))
        await card.play(player, target)

        if isinstance(game.controller, PlayCardController):
            # 如果当前控制器是 PlayCardController，则切换到下一个玩家
            await game.next_turn()

        return True


class CannotPlayCardMsg(Msg):
    def __init__(self, player: "Player", card: Card, reason: str):
        self.player = player
        self.card = card
        self.reason = reason

    def __str__(self):
        return f"无法打出卡牌[{self.card.name}]: {self.reason}"


class MustFirstMsg(Msg):
    def __init__(self):
        super().__init__("第一张牌必须是第一发现人")


class NotYourTurnMsg(Msg):
    def __init__(self):
        super().__init__("还没到你的回合")


class CardPlayedMsg(Msg):
    def __init__(
        self, player: "Player", card_name: str, target: Optional["Player"] = None
    ):
        self.player = player
        self.card_name = card_name
        self.target = target

    def __str__(self):
        if self.target:
            return f"玩家{self.player.id}对玩家{self.target.id}打出了[{self.card_name}]"
        return f"玩家{self.player.id}打出了[{self.card_name}]"
