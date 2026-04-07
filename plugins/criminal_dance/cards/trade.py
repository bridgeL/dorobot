from ..card import Card
from ..controller import Controller
from ..msg import Msg
from ..player import Player


class TradeCard(Card):
    name = "交易"
    desc = "指定另一名玩家与你交换一张手牌。若任何一方没有手牌，此牌失效"

    need_target = True

    async def play(self, player, target):
        game = player.game
        players: list[Player] = [player, target]
        no_card_players = [p for p in players if len(p.cards) == 0]

        if no_card_players:
            await game.notify(TradeNoEffectMsg(no_card_players))
            return

        await game.notify(TradeStartHintMsg(players))
        game.controller = TradeController(game, player, target)


class TradeController(Controller):
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

            # 移除玩家的卡牌
            player.cards.remove(card)
            self.card1 = card
            return True

        if player.id == self.player2.id:
            if self.card2 is not None:
                await self.game.notify(TradeRejectedDuplicateCardMsg(player))
                return False

            # 移除玩家的卡牌
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

        # 恢复controller
        await self.game.recover_controller()

    async def handle(self, player, card, target):
        # 设置交易
        if not await self.set_card(player, card):
            return False

        # 所有玩家都设置了交易
        if self.card1 is not None and self.card2 is not None:
            await self.finish()

        return True


class TradeRejectedDuplicateCardMsg(Msg):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return f"玩家{self.player.id}已经给过要交易的牌了"


class TradeRejectedInvalidPlayerMsg(Msg):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return f"玩家{self.player.id}不是交易的参与者"


class TradeNoEffectMsg(Msg):
    def __init__(self, players: list[Player]):
        self.players = players

    def __str__(self):
        s = ", ".join(f"玩家{p.id}" for p in self.players)
        return f"交易没有效果：{s}没有手牌"


class TradeStartHintMsg(Msg):
    def __init__(self, players: list[Player]):
        self.players = players

    def __str__(self):
        s = ", ".join(f"玩家{p.id}" for p in self.players)
        return f"请{s}给出要交易的牌"


class TradeResultMsg(Msg):
    def __init__(self, player: Player, prev_card: Card, card: Card):
        self.player = player
        self.prev_card = prev_card
        self.card = card

    def __str__(self):
        return f"玩家{self.player.id}失去了[{self.prev_card.name}]，获得了[{self.card.name}]"
