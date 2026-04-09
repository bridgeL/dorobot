import random
from ..msg import Msg
from ..player import Player
from ..card import Card


class RumorCard(Card):
    name = "谣言"
    desc = "所有有手牌的玩家参与谣言，每人随机抽一张他下家的手牌"

    async def play(self, player, target):
        game = player.game
        cards: list[Card] = []
        players: list[Player] = []

        for p in game.players:
            if p.cards:
                card = p.cards.pop(random.randint(0, len(p.cards) - 1))
                cards.append(card)
                players.append(p)

        # 交换
        prev_cards = cards.copy()
        cards.append(cards.pop(0))

        for prev_card, card, p in zip(prev_cards, cards, players):
            p.add_card(card)
            await game.notify(RumorResultMsg(p, prev_card, card), p)


class RumorResultMsg(Msg):
    def __init__(self, player: Player, prev_card: Card, card: Card):
        self.player = player
        self.prev_card = prev_card
        self.card = card

    def __str__(self):
        return f"{self.player.player_name}失去了[{self.prev_card.name}]，获得了[{self.card.name}]"