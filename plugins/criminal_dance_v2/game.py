import random
from typing import Optional
from .card import Card
from .controller import (
    Controller,
    PlayCardController,
    ExchangeInfoController,
    TradeController,
)
from .msg import Msg
from .player import Player
from .cards import (
    FirstCard,
    CriminalCard,
    DetectorCard,
    NotMeCard,
    BadGuyCard,
    SimpleCard,
    ExchangeInfoCard,
    RumorCard,
    TradeCard,
    WatcherCard,
    PoliceCard,
    DogCard,
)


class Game:
    def reset(self, num_players: int):
        self.num_players = num_players
        self.is_end = False
        self.is_first = True
        self.controller: Controller = PlayCardController(self)
        self.players = [Player(self, i) for i in range(num_players)]
        self.plugin = None
        self.group_id = None

    async def start(self):
        cards = self.create_cards()
        random.shuffle(cards)

        for i, card in enumerate(cards):
            self.players[i % self.num_players].cards.append(card)

            if card.name == FirstCard.name:
                self.current_player_index = i % self.num_players

        # 发牌信息给所有玩家
        for player in self.players:
            await self.notify(
                HandCardMsg(player.cards, self.num_players, player.player_id), player
            )

    def create_cards(self) -> list[Card]:
        num_players = self.num_players

        cards1 = [
            SimpleCard(),
            SimpleCard(),
            ExchangeInfoCard(),
            ExchangeInfoCard(),
            ExchangeInfoCard(),
            ExchangeInfoCard(),
            RumorCard(),
            RumorCard(),
            RumorCard(),
            RumorCard(),
            TradeCard(),
            TradeCard(),
            TradeCard(),
            TradeCard(),
            WatcherCard(),
            WatcherCard(),
            WatcherCard(),
            WatcherCard(),
        ]

        cards2 = [PoliceCard(), DogCard()]

        random.shuffle(cards1)
        random.shuffle(cards2)

        if num_players == 3:
            return [FirstCard(), CriminalCard(), DetectorCard(), NotMeCard()] + cards1[:8]

        if num_players == 4:
            return [
                FirstCard(),
                CriminalCard(),
                DetectorCard(),
                NotMeCard(),
                BadGuyCard(),
            ] + cards1[:11]

        if num_players == 5:
            return [
                FirstCard(),
                CriminalCard(),
                DetectorCard(),
                NotMeCard(),
                NotMeCard(),
                BadGuyCard(),
            ] + cards1[:14]

        if num_players == 6:
            return (
                [
                    FirstCard(),
                    CriminalCard(),
                    DetectorCard(),
                    DetectorCard(),
                    NotMeCard(),
                    NotMeCard(),
                    BadGuyCard(),
                    BadGuyCard(),
                ]
                + cards1[:15]
                + cards2[:1]
            )

        if num_players == 7:
            return (
                [
                    FirstCard(),
                    CriminalCard(),
                    DetectorCard(),
                    DetectorCard(),
                    NotMeCard(),
                    NotMeCard(),
                    NotMeCard(),
                    BadGuyCard(),
                    BadGuyCard(),
                ]
                + cards1
                + cards2[:1]
            )

        if num_players == 8:
            return (
                [
                    FirstCard(),
                    CriminalCard(),
                    DetectorCard(),
                    DetectorCard(),
                    DetectorCard(),
                    NotMeCard(),
                    NotMeCard(),
                    NotMeCard(),
                    NotMeCard(),
                    NotMeCard(),
                    BadGuyCard(),
                    BadGuyCard(),
                ]
                + cards1
                + cards2
            )

    async def recover_controller(self):
        self.controller = PlayCardController(self)
        await self.next_turn()

    def get_player(self, player_id: int) -> Player | None:
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    @property
    def current_player(self):
        return self.players[self.current_player_index]

    async def next_turn(self):
        if self.is_end:
            return

        self.is_first = False

        while True:
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            if self.current_player.cards:
                break

        await self.notify(YourTurnMsg(self.current_player))

    async def bad_win(self):
        self.is_end = True
        good_players = [p for p in self.players if not p.is_bad]
        bad_players = [p for p in self.players if p.is_bad]
        await self.notify(BadWinMsg(good_players, bad_players))

    async def good_win(self):
        self.is_end = True
        good_players = [p for p in self.players if not p.is_bad]
        bad_players = [p for p in self.players if p.is_bad]
        await self.notify(GoodWinMsg(good_players, bad_players))

    async def notify(self, msg: Msg, target: Optional[Player] = None):
        if self.plugin and hasattr(self.plugin, 'notify_game'):
            await self.plugin.notify_game(msg, target)
        elif not target:
            print("[公共消息]", msg)
        else:
            print("[私聊消息]", f"@{target.player_name}", msg)


class BadWinMsg(Msg):
    def __init__(self, good_players: list[Player], bad_players: list[Player]):
        self.good_players = good_players
        self.bad_players = bad_players

    def __str__(self):
        s = ", ".join(p.player_name for p in self.bad_players)
        return f"坏人阵营获胜：{s}"


class GoodWinMsg(Msg):
    def __init__(self, good_players: list[Player], bad_players: list[Player]):
        self.good_players = good_players
        self.bad_players = bad_players

    def __str__(self):
        s = ", ".join(p.player_name for p in self.good_players)
        return f"好人阵营获胜：{s}"


class YourTurnMsg(Msg):
    def __init__(self, player: Player):
        self.player = player

    def __str__(self):
        return f"轮到{self.player.player_name}出牌"


class HandCardMsg(Msg):
    def __init__(self, cards: list[Card], num_players: int, player_id: int):
        self.cards = cards
        self.num_players = num_players
        self.player_id = player_id

    def __str__(self):
        return f"你的手牌：{self.cards}"

    def get_data(self):
        return {
            "type": "hand_card",
            "data": {
                "cards": [{"name": c.name, "desc": c.desc} for c in self.cards],
                "num_players": self.num_players,
                "player_id": self.player_id,
            },
        }