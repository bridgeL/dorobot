from ..card import Card
from ..msg import Msg
from ..player import Player


class WatcherCard(Card):
    name = "目击者"
    desc = "看另一个玩家的手牌"

    need_target = True

    async def play(self, player, target):
        game = player.game
        if target.cards:
            await game.notify(WatchResultMsg(target), player)
        else:
            await game.notify(WatchNothingMsg(target), player)


class WatchNothingMsg(Msg):
    def __init__(self, target: Player):
        self.target = target

    def __str__(self):
        return f"玩家{self.target.id}没有手牌"


class WatchResultMsg(Msg):
    def __init__(self, target: Player):
        self.target = target

    def __str__(self):
        hand_cards = [card.name for card in self.target.cards]
        return f"玩家{self.target.id}的手牌是: {', '.join(hand_cards)}"
