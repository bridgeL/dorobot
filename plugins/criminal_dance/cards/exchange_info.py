from typing import Optional
from ..card import Card
from ..msg import Msg
from ..player import Player
from ..controller import Controller


class ExchangeInfoCard(Card):
    name = "情报交换"
    desc = "所有有手牌的玩家参与交换，每人把一张牌传给他上家"

    async def play(self, player, target):
        game = player.game

        # 所有有手牌的玩家参与情报交换
        players = [p for p in game.players if p.cards]

        # 通过私聊分别提示每个玩家
        for p in players:
            await game.notify(ExchangeStartHintMsg([p]), p)
        game.controller = ExchangeInfoController(game, players)


class ExchangeInfoController(Controller):
    def __init__(self, game, players: list[Player]):
        super().__init__(game)
        self.data: dict[Player, Optional[Card]] = {}

        # 初始化记录
        for player in players:
            self.data[player] = None

    async def set_card(self, player: Player, card: Card) -> bool:
        # 检查玩家是否可以参与情报交换
        if player not in self.data.keys():
            await self.game.notify(ExchangeRejectedInvalidPlayerMsg(player))
            return False

        # 检查玩家是否已经设置了情报交换信息
        if self.data[player] is not None:
            await self.game.notify(ExchangeRejectedDuplicateCardMsg(player))
            return False

        # 移除玩家的卡牌
        player.cards.remove(card)
        self.data[player] = card
        return True

    async def finish(self):
        # 交换
        players = list(self.data.keys())
        cards = list(self.data.values())
        prev_cards = cards.copy()
        cards.append(cards.pop(0))

        for prev_card, card, player in zip(prev_cards, cards, players):
            player.add_card(card)
            await self.game.notify(ExchangeResultMsg(player, prev_card, card), player)

        # 恢复controller
        await self.game.recover_controller()

    async def handle(self, player, card, target):
        # 设置情报交换的卡牌
        if not await self.set_card(player, card):
            return False

        # 所有玩家都设置了情报交换信息
        if all(card is not None for card in self.data.values()):
            await self.finish()

        return True


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
