"""卡牌模块"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Card:
    """卡牌基类"""
    name: str          # 卡牌显示名称
    card_type: str      # card type: identity / info / trade
    description: str    # 卡牌描述

    def __hash__(self):
        return hash(self.name)


# ============ 卡牌定义 ============

CARDS = {
    # 身份牌
    "第一发现人": Card("第一发现人", "identity", "必须为全局第一张打出的牌"),
    "犯人": Card("犯人", "identity", "打出后坏人获胜；若手牌被质疑则好人获胜"),
    "侦探": Card("侦探", "identity", "质疑目标——若对方有犯人且无不在场证明，好人获胜"),
    "警部": Card("警部", "identity", "指定玩家——若该玩家最终打出犯人牌，好人获胜"),
    "不在场证明": Card("不在场证明", "identity", "被动：被侦探质疑时可否认"),
    "共犯": Card("共犯", "identity", "打出后立即加入坏人阵营"),
    "神犬": Card("神犬", "identity", "目标弃一张牌——若弃的是犯人牌好人获胜"),
    "普通人": Card("普通人", "identity", "无效果"),

    # 情报/交换牌
    "谣言": Card("谣言", "info", "所有有手牌的玩家随机抽一张下家的手牌"),
    "情报交换": Card("情报交换", "info", "所有有手牌的玩家将一张牌传给他上家"),
    "目击者": Card("目击者", "info", "查看目标玩家的手牌"),

    # 交易牌
    "交易": Card("交易", "trade", "与目标玩家互相交换一张手牌"),
}


def get_card(name: str) -> Optional[Card]:
    """根据名称获取卡牌"""
    return CARDS.get(name)


def get_all_cards() -> list[Card]:
    """获取所有卡牌"""
    return list(CARDS.values())


def generate_card_pool(player_count: int) -> list[Card]:
    """根据玩家人数生成卡牌池"""
    import random

    # 补充牌池1：18张
    pool1 = [
        "普通人", "普通人",
        "情报交换", "情报交换", "情报交换", "情报交换",
        "谣言", "谣言", "谣言", "谣言",
        "交易", "交易", "交易", "交易",
        "目击者", "目击者", "目击者", "目击者",
    ]

    # 补充牌池2：2张（警部、神犬）
    pool2 = ["警部", "神犬"]

    random.shuffle(pool1)
    random.shuffle(pool2)

    pool = []

    # 固定牌
    if player_count == 3:
        pool = ["第一发现人", "犯人", "侦探", "不在场证明"]
        pool.extend(pool1[:8])
    elif player_count == 4:
        pool = ["第一发现人", "犯人", "侦探", "不在场证明", "共犯"]
        pool.extend(pool1[:11])
    elif player_count == 5:
        pool = ["第一发现人", "犯人", "侦探", "不在场证明", "不在场证明", "共犯"]
        pool.extend(pool1[:14])
    elif player_count == 6:
        pool = ["第一发现人", "犯人", "侦探", "侦探", "不在场证明", "不在场证明", "共犯", "共犯"]
        pool.extend(pool1[:15])
        pool.append(pool2[0])
    elif player_count == 7:
        pool = ["第一发现人", "犯人", "侦探", "侦探", "不在场证明", "不在场证明", "不在场证明", "共犯", "共犯"]
        pool.extend(pool1)
        pool.append(pool2[0])
    elif player_count == 8:
        pool = ["第一发现人", "犯人", "侦探", "侦探", "侦探", "不在场证明", "不在场证明", "不在场证明", "不在场证明", "不在场证明", "共犯", "共犯"]
        pool.extend(pool1)
        pool.extend(pool2)

    random.shuffle(pool)
    return [get_card(c) for c in pool]


def generate_fixed_pool(card_names: list[str]) -> list[Card]:
    """生成固定顺序的卡牌池（用于测试）

    Args:
        card_names: 卡牌名称列表
    """
    return [get_card(c) for c in card_names]


def deal_cards(pool: list[Card], player_count: int) -> list[list[Card]]:
    """发牌给所有玩家，每人4张，返回玩家手牌列表"""
    cards_per_player = 4
    hands = []
    for i in range(player_count):
        player_cards = pool[i * cards_per_player : (i + 1) * cards_per_player]
        hands.append(player_cards)
    return hands
