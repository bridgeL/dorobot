from ..card import Card


class BadGuyCard(Card):
    name = "共犯"
    desc = "打出这张牌成为共犯，加入坏人阵营"

    async def play(self, player, target):
        player.is_bad = True
