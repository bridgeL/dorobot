from typing import TYPE_CHECKING, Optional
from .card import Card

if TYPE_CHECKING:
    from .game import Game


class Player:
    def __init__(self, game: "Game", id: int):
        self.id = id
        self.player_id: str = str(id)  # 实际用户ID
        self.player_name: str = f"玩家{id}"  # 实际用户名
        self.cards: list[Card] = []
        self.game = game
        self.is_bad = False
        self.is_monitored_by_police: Player | None = None  # 被警察监视

    async def play_card(self, card: Card, target: Optional["Player"] = None) -> bool:
        return await self.game.controller.handle(self, card, target)

    def get_card(self, card_name: str) -> Card | None:
        for card in self.cards:
            if card.name == card_name:
                return card
        return None

    def add_card(self, card: Card) -> None:
        self.cards.append(card)

    def __str__(self):
        return f"Player {self.id} ({self.cards})"

    def __repr__(self):
        return str(self)