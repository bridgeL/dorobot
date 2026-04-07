from ..card import Card
from ..msg import Msg


class CriminalCard(Card):
    name = "犯人"
    desc = "此牌只能作为你的最后一张手牌打出。打出此牌成为犯人，你和坏人阵营获胜。若持有此卡被抓到，你和坏人阵营失败"

    max_num_card = 1

    async def play(self, player, target):
        game = player.game
        monitor = player.is_monitored_by_police

        # 被警部抓到
        if monitor:
            monitor.is_bad = False
            player.is_bad = True
            await game.notify(CriminalCatchedMsg())
            await game.good_win()

        else:
            player.is_bad = True
            await game.notify(CriminalEscapeMsg())
            await game.bad_win()


class CriminalCatchedMsg(Msg):
    def __init__(self):
        super().__init__("犯人被蹲点的警部抓到了")


class CriminalEscapeMsg(Msg):
    def __init__(self):
        super().__init__("犯人成功逃走了")
