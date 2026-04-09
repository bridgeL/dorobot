from ..card import Card


class FirstCard(Card):
    name = "第一发现人"
    desc = "你发现了尸体，此牌必须是全局第一张打出的牌"

    async def play(self, player, target):
        player.game.is_first = False