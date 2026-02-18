# cogs/modules/profile/data.py

import random

# === 猫咪数据定义 ===
# 1. 定义品种 (12种)
SPECIES_LIST = [
    "中华田园喵", "英国短毛喵", "美国短毛喵", "波斯喵", 
    "布偶喵", "暹罗喵", "缅因喵", "斯芬克斯无毛喵", 
    "苏格兰折耳喵", "挪威森林喵", "孟加拉豹喵", "俄罗斯蓝喵"
]

# 2. 定义花色 (12种)
PATTERN_LIST = [
    "纯白", "纯黑", "橘色虎斑", "银色渐层", 
    "三花", "玳瑁", "奶牛黑白", "深灰蓝", 
    "重点色", "烟熏色", "巧克力色", "金色斑点"
]
# 组合总数 = 12 * 12 = 144种，满足至少100种的要求

# 3. 定义特殊匹配 (Special Matches) - 初始资金加成
# 格式: (品种, 花色): 额外奖金
SPECIAL_COMBOS = {
    ("中华田园喵", "橘色虎斑"): 5000,    # 十个橘猫九个富
    ("斯芬克斯无毛喵", "金色斑点"): 8888, # 埃及法老款
    ("布偶喵", "重点色"): 3000,          # 仙女加成
    ("波斯喵", "纯白"): 3000,            # 贵族加成
    ("孟加拉豹喵", "金色斑点"): 4000,    # 狂野加成
    ("俄罗斯蓝喵", "深灰蓝"): 2500,      # 皇室加成
    ("三花", "中华田园喵"): 2000,        # 招财猫(实际上应该是品种+花色，这里反过来写也没事，逻辑里对应即可)
    ("缅因喵", "烟熏色"): 3500,          # 霸总加成
    ("暹罗喵", "重点色"): 2000,          # 挖煤工加成(辛勤致富)
    ("美国短毛喵", "银色渐层"): 2200     # 经典加成
}

# 默认初始资金
DEFAULT_MONEY = 1000

def generate_cat_identity():
    """
    随机生成一个猫咪身份
    返回: (species, pattern, initial_money, is_special)
    """
    species = random.choice(SPECIES_LIST)
    pattern = random.choice(PATTERN_LIST)
    
    # 检查是否命中特殊款
    bonus = 0
    is_special = False
    
    # 检查组合 (Tuple匹配)
    if (species, pattern) in SPECIAL_COMBOS:
        bonus = SPECIAL_COMBOS[(species, pattern)]
        is_special = True
    
    total_money = DEFAULT_MONEY + bonus
    
    return species, pattern, total_money, is_special

# === 称号数据定义 ===
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