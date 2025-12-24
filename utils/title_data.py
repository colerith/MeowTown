# utils/title_data.py
import random

# 抽一次的价格
TITLE_DRAW_COST = 500

# 稀有度定义
RARITY_CONFIG = {
    "N": {"name": "普通", "color": 0x95a5a6, "prob": 0.50},   # 50%
    "R": {"name": "稀有", "color": 0x3498db, "prob": 0.30},   # 30%
    "SR": {"name": "史诗", "color": 0x9b59b6, "prob": 0.15},  # 15%
    "SSR": {"name": "传说", "color": 0xf1c40f, "prob": 0.05}  # 5%
}

# 称号库 (ID: {name, rarity})
TITLES = {
    # --- 普通 (N) ---
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

    # --- 稀有 (R) ---
    "11": {"name": "捕鼠能手", "rarity": "R"},
    "12": {"name": "键盘破坏者", "rarity": "R"},
    "13": {"name": "股市韭菜", "rarity": "R"},
    "14": {"name": "猫薄荷瘾君子", "rarity": "R"},
    "15": {"name": "优雅贵族", "rarity": "R"},
    "16": {"name": "农场主", "rarity": "R"},
    "17": {"name": "鱼骨收藏家", "rarity": "R"},

    # --- 史诗 (SR) ---
    "18": {"name": "喵尔街之狼", "rarity": "SR"},
    "19": {"name": "地产大亨", "rarity": "SR"},
    "20": {"name": "顶级掠食者", "rarity": "SR"},
    "21": {"name": "魔法学徒", "rarity": "SR"},
    "22": {"name": "九命猫妖", "rarity": "SR"},

    # --- 传说 (SSR) ---
    "23": {"name": "喵星人", "rarity": "SSR"},
    "24": {"name": "镇长候选人", "rarity": "SSR"},
    "25": {"name": "创世之爪", "rarity": "SSR"}
}

def draw_random_title():
    """根据概率随机抽取一个称号"""
    rand = random.random()
    cumulative = 0.0
    
    # 1. 确定稀有度
    target_rarity = "N"
    # 按 N -> R -> SR -> SSR 的顺序或者反过来都可以，这里按配置概率累加
    # 为了简单，我们硬编码概率区间
    if rand < 0.50: target_rarity = "N"
    elif rand < 0.80: target_rarity = "R"
    elif rand < 0.95: target_rarity = "SR"
    else: target_rarity = "SSR"
    
    # 2. 从该稀有度中随机选一个
    candidates = [tid for tid, data in TITLES.items() if data["rarity"] == target_rarity]
    title_id = random.choice(candidates)
    
    return title_id, TITLES[title_id]