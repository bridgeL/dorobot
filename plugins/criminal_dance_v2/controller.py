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

        # 切换到下一个玩家
        await game.next_turn()

        return True


class ExchangeInfoController(Controller):
    """情报交换控制器"""

    def __init__(self, game, players: list[Player]):
        super().__init__(game)
        self.data: dict[Player, Optional[Card]] = {}
        for player in players:
            self.data[player] = None

    async def set_card(self, player: Player, card: Card) -> bool:
        if player not in self.data.keys():
            await self.game.notify(ExchangeRejectedInvalidPlayerMsg(player))
            return False
        if self.data[player] is not None:
            await self.game.notify(ExchangeRejectedDuplicateCardMsg(player))
            return False

        player.cards.remove(card)
        self.data[player] = card
        return True

    async def finish(self):
        players = list(self.data.keys())
        cards = list(self.data.values())
        prev_cards = cards.copy()
        cards.append(cards.pop(0))

        for prev_card, card, player in zip(prev_cards, cards, players):
            player.add_card(card)
            await self.game.notify(ExchangeResultMsg(player, prev_card, card), player)

        await self.game.recover_controller()

    async def handle(self, player, card, target):
        if not await self.set_card(player, card):
            return False
        if all(c is not None for c in self.data.values()):
            await self.finish()
        return True


class TradeController(Controller):
    """交易控制器"""

    def __init__(self, game, player1: Player, player2: Player):
        super().__init__(game)
        self.player1 = player1
        self.player2 = player2
        self.card1: Card | None = None
        self.card2: Card | None = None

    async def set_card(self, player: Player, card: Card) -> bool:
        if player.id == self.player1.id:
            if self.card1 is not None:
                await self.game.notify(TradeRejectedDuplicateCardMsg(player))
                return False
            player.cards.remove(card)
            self.card1 = card
            return True

        if player.id == self.player2.id:
            if self.card2 is not None:
                await self.game.notify(TradeRejectedDuplicateCardMsg(player))
                return False
            player.cards.remove(card)
            self.card2 = card
            return True

        await self.game.notify(TradeRejectedInvalidPlayerMsg(player))
        return False

    async def finish(self):
        self.player1.cards.append(self.card2)
        self.player2.cards.append(self.card1)

        await self.game.notify(
            TradeResultMsg(self.player1, self.card1, self.card2), self.player1
        )
        await self.game.notify(
            TradeResultMsg(self.player2, self.card2, self.card1), self.player2
        )

        await self.game.recover_controller()

    async def handle(self, player, card, target):
        if not await self.set_card(player, card):
            return False
        if self.card1 is not None and self.card2 is not None:
            await self.finish()
        return True


# ========== 消息类 ==========

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
    def __init__(self, player: "Player", card_name: str, target: Optional["Player"] = None):
        self.player = player
        self.card_name = card_name
        self.target = target

    def __str__(self):
        if self.target:
            return f"{self.player.player_name}对{self.target.player_name}打出了[{self.card_name}]"
        return f"{self.player.player_name}打出了[{self.card_name}]"


class ExchangeStartHintMsg(Msg):
    def __init__(self, players: list[Player]):
        self.players = players

    def __str__(self):
        s = ", ".join(p.player_name for p in self.players)
        return f"请{s}给出要交换的牌"


class ExchangeRejectedInvalidPlayerMsg(Msg):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return f"{self.player.player_name}不是情报交换的参与者"


class ExchangeRejectedDuplicateCardMsg(Msg):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return f"{self.player.player_name}已经给过牌了"


class ExchangeResultMsg(Msg):
    def __init__(self, player: Player, prev_card: Card, card: Card):
        self.player = player
        self.prev_card = prev_card
        self.card = card

    def __str__(self):
        return f"{self.player.player_name}失去了[{self.prev_card.name}]，获得了[{self.card.name}]"


class TradeRejectedDuplicateCardMsg(Msg):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return f"{self.player.player_name}已经给过要交易的牌了"


class TradeRejectedInvalidPlayerMsg(Msg):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return f"{self.player.player_name}不是交易的参与者"


class TradeNoEffectMsg(Msg):
    def __init__(self, players: list[Player]):
        self.players = players

    def __str__(self):
        s = ", ".join(p.player_name for p in self.players)
        return f"交易没有效果：{s}没有手牌"


class TradeStartHintMsg(Msg):
    def __init__(self, players: list[Player]):
        self.players = players

    def __str__(self):
        s = ", ".join(p.player_name for p in self.players)
        return f"请{s}给出要交易的牌"


class TradeResultMsg(Msg):
    def __init__(self, player: Player, prev_card: Card, card: Card):
        self.player = player
        self.prev_card = prev_card
        self.card = card

    def __str__(self):
        return f"{self.player.player_name}失去了[{self.prev_card.name}]，获得了[{self.card.name}]"