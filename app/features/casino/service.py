import random
from datetime import datetime, timedelta, timezone
from itertools import combinations


SAVINGS_LOCK_DAYS = 7
PLAYER_ROB_SUCCESS_BASE_RATE = 0.5
PLAYER_ROB_SUCCESS_MIN_RATE = 0.1
BANK_ROB_SUCCESS_RATE = 0.08
JAIL_MINUTES_ON_FAILED_ROB = 15
DUEL_JAIL_EXTENSION_MINUTES = 10
MAX_BRIBES_PER_DAY = 3

CARD_RANK_VALUES = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14,
}
POKER_HAND_NAMES = {
    10: "皇家同花顺",
    9: "同花顺",
    8: "四条",
    7: "葫芦",
    6: "同花",
    5: "顺子",
    4: "三条",
    3: "两对",
    2: "一对",
    1: "高牌",
}
def get_utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_positive_int(value):
    amount = int(value)
    if amount <= 0:
        raise ValueError("amount must be positive")
    return amount


def compute_savings_unlock_time(now=None):
    now = now or get_utc_now()
    return now + timedelta(days=SAVINGS_LOCK_DAYS)


def is_sentence_active(sentence_ends_at, now=None):
    if sentence_ends_at is None:
        return False
    now = now or get_utc_now()
    return now < sentence_ends_at


def calculate_player_rob_success_rate(thief_level, victim_level):
    safe_thief = max(1, int(thief_level or 1))
    safe_victim = max(1, int(victim_level or 1))
    level_diff = max(0, safe_victim - safe_thief)
    return max(PLAYER_ROB_SUCCESS_MIN_RATE, PLAYER_ROB_SUCCESS_BASE_RATE - level_diff * 0.01)


def roll_slots(bet):
    emojis = ["🍒", "🍊", "🍋", "🍉", "🍇", "💰", "💎", "7️⃣"]
    reels = [random.choice(emojis) for _ in range(3)]

    payout = 0
    if reels[0] == reels[1] == reels[2]:
        if reels[0] == "7️⃣":
            payout = bet * 77
        elif reels[0] == "💎":
            payout = bet * 50
        elif reels[0] == "💰":
            payout = bet * 25
        else:
            payout = bet * 10
    elif reels[0] == reels[1] or reels[1] == reels[2]:
        payout = bet * 2

    return reels, payout


def roll_dice_battle():
    player_dice = [random.randint(1, 6) for _ in range(2)]
    dealer_dice = [random.randint(1, 6) for _ in range(2)]
    return player_dice, dealer_dice, sum(player_dice), sum(dealer_dice)


def determine_player_robbery_loot(victim_balance):
    safe_balance = max(0, int(victim_balance))
    if safe_balance <= 0:
        return 0
    min_loot = max(1, int(safe_balance * 0.1))
    max_loot = max(min_loot, int(safe_balance * 0.3))
    return random.randint(min_loot, max_loot)


def determine_bank_robbery_loot(total_pool):
    safe_pool = max(0, int(total_pool))
    if safe_pool <= 0:
        return 0
    min_loot = max(1, int(safe_pool * 0.001))
    max_loot = max(min_loot, int(safe_pool * 0.005))
    return random.randint(min_loot, max_loot)


def roll_guard_duel():
    player_total = sum(random.randint(1, 6) for _ in range(2))
    guard_total = sum(random.randint(1, 6) for _ in range(2))
    return player_total, guard_total


def create_poker_deck():
    ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
    suits = ["♥️", "♦️", "♣️", "♠️"]
    return [{"rank": rank, "suit": suit} for rank in ranks for suit in suits]


def calculate_blackjack_score(hand):
    score = 0
    aces = 0
    for card in hand:
        if card["rank"] in {"J", "Q", "K"}:
            score += 10
        elif card["rank"] == "A":
            score += 11
            aces += 1
        else:
            score += int(card["rank"])

    while score > 21 and aces:
        score -= 10
        aces -= 1
    return score


def format_cards(cards):
    card_parts = [f"[{card['rank']}{card['suit']}]" for card in cards]
    return f"`{' '.join(card_parts)}`"


def rank_five_card_hand(hand):
    values = sorted([CARD_RANK_VALUES[card["rank"]] for card in hand], reverse=True)
    suits = [card["suit"] for card in hand]
    is_flush = len(set(suits)) == 1
    is_straight = (max(values) - min(values) == 4 and len(set(values)) == 5) or (values == [14, 5, 4, 3, 2])
    if values == [14, 5, 4, 3, 2]:
        values = [5, 4, 3, 2, 1]

    if is_straight and is_flush:
        return (10, values) if max(values) == 14 else (9, values)

    value_counts = {value: values.count(value) for value in values}
    counts = sorted(value_counts.values(), reverse=True)

    if counts == [4, 1]:
        four = [value for value, count in value_counts.items() if count == 4][0]
        return 8, [four]
    if counts == [3, 2]:
        three = [value for value, count in value_counts.items() if count == 3][0]
        return 7, [three]
    if is_flush:
        return 6, values
    if is_straight:
        return 5, values
    if counts == [3, 1, 1]:
        three = [value for value, count in value_counts.items() if count == 3][0]
        return 4, [three]
    if counts == [2, 2, 1]:
        pairs = [value for value, count in value_counts.items() if count == 2]
        return 3, sorted(pairs, reverse=True)
    if counts == [2, 1, 1, 1]:
        pair = [value for value, count in value_counts.items() if count == 2][0]
        return 2, [pair]
    return 1, values


def evaluate_seven_cards(seven_cards):
    best_hand_rank = (0, [])
    for hand in combinations(seven_cards, 5):
        hand_rank = rank_five_card_hand(list(hand))
        if hand_rank[0] > best_hand_rank[0]:
            best_hand_rank = hand_rank
        elif hand_rank[0] == best_hand_rank[0]:
            if not best_hand_rank[1] or max(hand_rank[1]) > max(best_hand_rank[1]):
                best_hand_rank = hand_rank
    return best_hand_rank, POKER_HAND_NAMES.get(best_hand_rank[0], "错误")


def deal_texas_holdem_round():
    deck = create_poker_deck()
    random.shuffle(deck)
    player_hand = [deck.pop(), deck.pop()]
    dealer_hand = [deck.pop(), deck.pop()]
    community_cards = [deck.pop() for _ in range(5)]
    player_rank, player_name = evaluate_seven_cards(player_hand + community_cards)
    dealer_rank, dealer_name = evaluate_seven_cards(dealer_hand + community_cards)
    return {
        "player_hand": player_hand,
        "dealer_hand": dealer_hand,
        "community_cards": community_cards,
        "player_rank": player_rank,
        "player_name": player_name,
        "dealer_rank": dealer_rank,
        "dealer_name": dealer_name,
    }


def roll_roulette_chamber():
    return random.randint(1, 6)


def roulette_survival_multiplier(shot_index):
    return [1.5, 2.2, 3.5, 6.0, 12.0][shot_index - 1]


def format_remaining_minutes(sentence_ends_at, now=None):
    if sentence_ends_at is None:
        return 0
    now = now or get_utc_now()
    remaining_seconds = max(0, int((sentence_ends_at - now).total_seconds()))
    return remaining_seconds // 60


__all__ = [
    "BANK_ROB_SUCCESS_RATE",
    "DUEL_JAIL_EXTENSION_MINUTES",
    "JAIL_MINUTES_ON_FAILED_ROB",
    "MAX_BRIBES_PER_DAY",
    "SAVINGS_LOCK_DAYS",
    "calculate_player_rob_success_rate",
    "calculate_blackjack_score",
    "compute_savings_unlock_time",
    "determine_bank_robbery_loot",
    "determine_player_robbery_loot",
    "format_remaining_minutes",
    "format_cards",
    "get_utc_now",
    "is_sentence_active",
    "parse_positive_int",
    "create_poker_deck",
    "deal_texas_holdem_round",
    "evaluate_seven_cards",
    "roulette_survival_multiplier",
    "roll_roulette_chamber",
    "roll_dice_battle",
    "roll_guard_duel",
    "roll_slots",
]
