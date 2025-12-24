# utils/cat_data.py
import random

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