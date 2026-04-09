from ..card import Card
from ..controller import ExchangeInfoController, ExchangeStartHintMsg


class ExchangeInfoCard(Card):
    name = "情报交换"
    desc = "所有有手牌的玩家参与交换，每人把一张牌传给他上家"

    async def play(self, player, target):
        game = player.game

        players = [p for p in game.players if p.cards]

        await game.notify(ExchangeStartHintMsg(players))
        game.controller = ExchangeInfoController(game, players)