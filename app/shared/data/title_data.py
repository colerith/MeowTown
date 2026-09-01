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

# 扩展称号库：保持原有 1-25 ID 不变，新增至 100 个。
EXTRA_TITLES = {
    "N": [
        "窗台观察员", "午睡实习生", "小鱼干搬运工", "毛球清洁工", "纸袋探险家", "阳光追逐者", "沙发守卫",
        "门缝侦察兵", "水杯推倒员", "凌晨跑酷员", "快递盒验收官", "尾巴追踪者", "猫砂质检员", "罐头开盖学徒",
        "暖气片居民", "被窝占领者", "拖鞋收藏员", "窗帘攀登者", "扫地机骑手", "塑料袋乐手", "饭点播报员",
        "摸鱼专员", "楼道巡逻猫", "纸团前锋", "逗猫棒陪练", "猫窝钉子户", "云朵打盹者", "喵语初学者",
    ],
    "R": [
        "金牌捕虫员", "阳台巡查官", "罐头品鉴家", "猫咖驻唱", "月光猎手", "屋顶信使", "鱼市采购官",
        "小镇调解员", "农田守望者", "幸运铃铛", "纸箱迷宫王", "猫薄荷园丁", "夜班保安喵", "沙发考古家",
        "毛线工程师", "地图测绘员", "银行排队王", "股票抄底猫", "骰子魔术师", "甜品试吃官", "雨夜巡游者",
        "星光向导",
    ],
    "SR": [
        "九街巡查使", "金枪鱼伯爵", "月影刺客", "翡翠猫眼", "皇家御膳官", "喵镇建筑师", "命运解读者",
        "星轨旅行家", "黄金肉垫", "百胜赌圣", "丰收大祭司", "幻境守门猫", "时空邮差", "深海寻宝王",
        "云端领航员",
    ],
    "SSR": [
        "永恒猫神", "星海领主", "万界铲屎官", "命运织爪者", "黄金城主", "银河捕鼠皇", "时间尽头之猫",
        "九霄喵帝", "猫薄荷圣者", "喵宇宙主宰",
    ],
}

for rarity, names in EXTRA_TITLES.items():
    for name in names:
        next_id = str(len(TITLES) + 1)
        TITLES[next_id] = {"name": name, "rarity": rarity}


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
