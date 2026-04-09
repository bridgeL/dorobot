from ..card import Card
from ..player import Player
from ..controller import TradeController, TradeNoEffectMsg, TradeStartHintMsg


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