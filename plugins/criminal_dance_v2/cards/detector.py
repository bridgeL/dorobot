from ..msg import Msg
from ..card import Card
from .not_me import NotMeCard
from .criminal import CriminalCard


class DetectorCard(Card):
    name = "侦探"
    desc = "只能在手牌数<=2时打出。打出时质疑另一位玩家，如果该玩家持有犯人，而且没有不在场证明，你和好人阵营获胜"

    max_num_card = 2
    need_target = True

    async def play(self, player, target):
        game = player.game
        if target.get_card(CriminalCard.name) and not target.get_card(NotMeCard.name):
            player.is_bad = False
            target.is_bad = True
            await game.notify(DetectorSuccessMsg())
            await game.good_win()
        else:
            await game.notify(DetectorFailMsg())


class DetectorFailMsg(Msg):
    def __init__(self):
        super().__init__("它不是犯人，或者有不在场证明")


class DetectorSuccessMsg(Msg):
    def __init__(self):
        super().__init__("侦探成功抓到了犯人")