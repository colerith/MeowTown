import random


SPECIES_LIST = [
    "中华田园喵", "英国短毛喵", "美国短毛喵", "波斯喵",
    "布偶喵", "暹罗喵", "缅因喵", "斯芬克斯无毛喵",
    "苏格兰折耳喵", "挪威森林喵", "孟加拉豹喵", "俄罗斯蓝喵",
]

PATTERN_LIST = [
    "纯白", "纯黑", "橘色虎斑", "银色渐层",
    "三花", "玳瑁", "奶牛黑白", "深灰蓝",
    "重点色", "烟熏色", "巧克力色", "金色斑点",
]

SPECIAL_COMBOS = {
    ("中华田园喵", "橘色虎斑"): 5000,
    ("斯芬克斯无毛喵", "金色斑点"): 8888,
    ("布偶喵", "重点色"): 3000,
    ("波斯喵", "纯白"): 3000,
    ("孟加拉豹喵", "金色斑点"): 4000,
    ("俄罗斯蓝喵", "深灰蓝"): 2500,
    ("三花", "中华田园喵"): 2000,
    ("缅因喵", "烟熏色"): 3500,
    ("暹罗喵", "重点色"): 2000,
    ("美国短毛喵", "银色渐层"): 2200,
}

DEFAULT_MONEY = 1000
TITLE_DRAW_COST = 500

RARITY_CONFIG = {
    "N": {"name": "普通", "color": 0x95A5A6, "prob": 0.50},
    "R": {"name": "稀有", "color": 0x3498DB, "prob": 0.30},
    "SR": {"name": "史诗", "color": 0x9B59B6, "prob": 0.15},
    "SSR": {"name": "传说", "color": 0xF1C40F, "prob": 0.05},
}

TITLES = {
    "1": {"name": "流浪小猫", "rarity": "N"},
    "2": {"name": "铲屎官", "rarity": "N"},
    "3": {"name": "打工人", "rarity": "N"},
    "4": {"name": "呼噜怪", "rarity": "N"},
    "5": {"name": "掉毛怪", "rarity": "N"},
    "6": {"name": "罐头鉴定师", "rarity": "N"},
    "7": {"name": "纸箱建筑师", "rarity": "N"},
    "8": {"name": "小镇路人A", "rarity": "N"},
    "9": {"name": "熬夜冠军", "rarity": "N"},
    "10": {"name": "咸鱼", "rarity": "N"},
    "11": {"name": "捕鼠能手", "rarity": "R"},
    "12": {"name": "键盘破坏者", "rarity": "R"},
    "13": {"name": "股市韭菜", "rarity": "R"},
    "14": {"name": "猫薄荷瘾君子", "rarity": "R"},
    "15": {"name": "优雅贵族", "rarity": "R"},
    "16": {"name": "农场主", "rarity": "R"},
    "17": {"name": "鱼骨收藏家", "rarity": "R"},
    "18": {"name": "喵尔街之狼", "rarity": "SR"},
    "19": {"name": "地产大亨", "rarity": "SR"},
    "20": {"name": "顶级掠食者", "rarity": "SR"},
    "21": {"name": "魔法学徒", "rarity": "SR"},
    "22": {"name": "九命猫妖", "rarity": "SR"},
    "23": {"name": "喵星人", "rarity": "SSR"},
    "24": {"name": "镇长候选人", "rarity": "SSR"},
    "25": {"name": "创世之爪", "rarity": "SSR"},
}


def generate_cat_identity():
    species = random.choice(SPECIES_LIST)
    pattern = random.choice(PATTERN_LIST)

    bonus = 0
    is_special = False
    if (species, pattern) in SPECIAL_COMBOS:
        bonus = SPECIAL_COMBOS[(species, pattern)]
        is_special = True

    total_money = DEFAULT_MONEY + bonus
    return species, pattern, total_money, is_special


def draw_random_title():
    rand = random.random()
    if rand < 0.50:
        target_rarity = "N"
    elif rand < 0.80:
        target_rarity = "R"
    elif rand < 0.95:
        target_rarity = "SR"
    else:
        target_rarity = "SSR"

    candidates = [tid for tid, data in TITLES.items() if data["rarity"] == target_rarity]
    title_id = random.choice(candidates)
    return title_id, TITLES[title_id]


__all__ = [
    "DEFAULT_MONEY",
    "PATTERN_LIST",
    "RARITY_CONFIG",
    "SPECIAL_COMBOS",
    "SPECIES_LIST",
    "TITLES",
    "TITLE_DRAW_COST",
    "draw_random_title",
    "generate_cat_identity",
]
