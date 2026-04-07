from ..card import Card


class PoliceCard(Card):
    name = "警部"
    desc = "只能在手牌数<=2时打出。选定任意一个玩家放置此牌，若其最终打出犯人牌，你和好人阵营获胜"

    max_num_card = 2
    need_target = True
    can_target_self = True

    async def play(self, player, target):
        target.is_monitored_by_police = player
