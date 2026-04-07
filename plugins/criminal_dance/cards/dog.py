from ..card import Card
from ..msg import Msg
from ..controller import Controller
from ..player import Player
from .criminal import CriminalCard


class DogCard(Card):
    name = "神犬"
    desc = "选择一个有手牌的其他玩家。该玩家弃掉一张手牌，并且获得神犬。如果他弃掉的是犯人牌，你和好人阵营获胜"

    need_target = True
    can_target_empty_player = False

    async def play(self, player, target):
        game = player.game
        await game.notify(DogStartHintMsg(target))
        game.controller = DogController(game, player, target, self)


class DogController(Controller):
    def __init__(self, game, player: Player, target: Player, dog_card: Card):
        super().__init__(game)
        self.player = player
        self.target = target
        self.dog_card = dog_card

    async def handle(self, player, card, target):
        if player.id != self.target.id:
            await self.game.notify(DogFailInvalidPlayerMsg(player))
            return False

        if card.name == CriminalCard.name:
            # 犯人牌被弃掉，好人阵营获胜
            self.player.is_bad = False
            self.target.is_bad = True
            await self.game.notify(DogWinMsg())
            await self.game.good_win()
            return True

        player.cards.remove(card)
        player.cards.append(self.dog_card)
        await self.game.notify(DogDiscardMsg(player, card))

        # 恢复controller
        await self.game.recover_controller()
        return True


class DogStartHintMsg(Msg):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return f"请{self.player.player_name}丢弃一张牌"


class DogFailInvalidPlayerMsg(Msg):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return f"{self.player.player_name}没被神犬咬"


class DogWinMsg(Msg):
    def __init__(self):
        super().__init__("神犬成功抓到了犯人")


class DogDiscardMsg(Msg):
    def __init__(self, player: Player, prev_card: Card):
        self.player = player
        self.prev_card = prev_card

    def __str__(self):
        return (
            f"{self.player.player_name}丢弃了[{self.prev_card.name}]，获得了[{DogCard.name}]"
        )
