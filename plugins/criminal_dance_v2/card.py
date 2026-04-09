from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .player import Player


class Card:
    name: str
    desc: str

    max_num_card: int = 4  # 只能在手牌数 <= 4 时打出
    need_target: bool = False  # 需要指定一个目标使用
    can_target_self: bool = False  # 可以对自己使用
    can_target_empty_player: bool = True  # 可以对没手牌的玩家使用

    def can_play(
        self, player: "Player", target: Optional["Player"]
    ) -> tuple[bool, str]:
        if len(player.cards) > self.max_num_card:
            return False, f"只能在手牌数<={self.max_num_card}时打出"

        if self.need_target:
            if target is None:
                return False, "需要指定一个玩家作为目标对象"
            if not self.can_target_self and target.id == player.id:
                return False, "此牌不能指定自己作为目标"
            if not self.can_target_empty_player and not target.cards:
                return False, "不能对没手牌的玩家使用"

        return True, ""

    async def play(self, player: "Player", target: Optional["Player"]):
        pass

    def __str__(self):
        return f"{self.name}"

    def __repr__(self):
        return str(self)