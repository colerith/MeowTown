# utils/farm_data.py
import random

# 稀有度定义
RARITY = {
    "N":   {"name": "普通", "color": 0x95a5a6, "rate": 0.5},   # 普通 (50% 刷出率)
    "R":   {"name": "稀有", "color": 0x3498db, "rate": 0.3},   # 稀有
    "SR":  {"name": "史诗", "color": 0x9b59b6, "rate": 0.15},  # 史诗
    "SSR": {"name": "传说", "color": 0xf1c40f, "rate": 0.05}   # 传说
}

# 植物数据库 (50种)
PLANTS = {
    # --- Level 1: 新手区 (N) ---
    "1": {"name": "普通猫草", "cost": 10, "time": 60, "min": 12, "max": 18, "rarity": "N", "icon": "🌱"},
    "2": {"name": "胡萝卜", "cost": 20, "time": 300, "min": 25, "max": 35, "rarity": "N", "icon": "🥕"}, 
    "3": {"name": "小麦", "cost": 15, "time": 180, "min": 18, "max": 28, "rarity": "N", "icon": "🌾"}, 
    "4": {"name": "土豆", "cost": 25, "time": 600, "min": 35, "max": 50, "rarity": "N", "icon": "🥔"}, 
    "5": {"name": "玉米", "cost": 30, "time": 900, "min": 40, "max": 60, "rarity": "N", "icon": "🌽"}, 
    "6": {"name": "番茄", "cost": 35, "time": 1200, "min": 45, "max": 70, "rarity": "N", "icon": "🍅"}, 
    "7": {"name": "卷心菜", "cost": 40, "time": 1800, "min": 55, "max": 80, "rarity": "N", "icon": "🥬"}, 
    "8": {"name": "草莓", "cost": 50, "time": 3600, "min": 70, "max": 100, "rarity": "N", "icon": "🍓"}, 
    "9": {"name": "向日葵", "cost": 60, "time": 5400, "min": 85, "max": 120, "rarity": "N", "icon": "🌻"}, 
    "10": {"name": "茄子", "cost": 70, "time": 7200, "min": 100, "max": 150, "rarity": "N", "icon": "🍆"}, 
    "11": {"name": "红辣椒", "cost": 80, "time": 10800, "min": 120, "max": 180, "rarity": "N", "icon": "🌶️"}, 
    "12": {"name": "南瓜", "cost": 90, "time": 14400, "min": 140, "max": 200, "rarity": "N", "icon": "🎃"}, 
    "13": {"name": "洋葱", "cost": 55, "time": 4800, "min": 75, "max": 110, "rarity": "N", "icon": "🧅"},
    "14": {"name": "大蒜", "cost": 65, "time": 6000, "min": 90, "max": 130, "rarity": "N", "icon": "🧄"},
    "15": {"name": "西兰花", "cost": 75, "time": 9000, "min": 110, "max": 160, "rarity": "N", "icon": "🥦"},
    "16": {"name": "樱桃", "cost": 100, "time": 18000, "min": 150, "max": 250, "rarity": "N", "icon": "🍒"}, 
    "17": {"name": "蜜桃", "cost": 110, "time": 21600, "min": 160, "max": 280, "rarity": "N", "icon": "🍑"}, 
    "18": {"name": "苹果", "cost": 120, "time": 25200, "min": 180, "max": 300, "rarity": "N", "icon": "🍎"}, 

    # --- Level 2: 进阶农作物 (R) ---
    "19": {"name": "发光蘑菇", "cost": 200, "time": 28800, "min": 300, "max": 500, "rarity": "R", "icon": "🍄"}, 
    "20": {"name": "蓝莓灌木", "cost": 250, "time": 36000, "min": 380, "max": 600, "rarity": "R", "icon": "🫐"}, 
    "21": {"name": "铃铛花", "cost": 300, "time": 43200, "min": 450, "max": 750, "rarity": "R", "icon": "🛎️"}, 
    "22": {"name": "逗猫棒草", "cost": 350, "time": 50400, "min": 550, "max": 850, "rarity": "R", "icon": "🎣"}, 
    "23": {"name": "毛线球花", "cost": 400, "time": 57600, "min": 650, "max": 950, "rarity": "R", "icon": "🧶"}, 
    "24": {"name": "西瓜", "cost": 450, "time": 64800, "min": 750, "max": 1100, "rarity": "R", "icon": "🍉"}, 
    "25": {"name": "菠萝", "cost": 500, "time": 72000, "min": 850, "max": 1250, "rarity": "R", "icon": "🍍"}, 
    "26": {"name": "咖啡豆", "cost": 550, "time": 86400, "min": 1000, "max": 1500, "rarity": "R", "icon": "☕"}, 
    "27": {"name": "纸箱树", "cost": 600, "time": 93600, "min": 1100, "max": 1600, "rarity": "R", "icon": "📦"}, 
    "28": {"name": "葡萄", "cost": 650, "time": 100800, "min": 1200, "max": 1800, "rarity": "R", "icon": "🍇"}, 
    "29": {"name": "奇异果", "cost": 700, "time": 108000, "min": 1300, "max": 1900, "rarity": "R", "icon": "🥝"}, 
    "30": {"name": "香蕉树", "cost": 750, "time": 115200, "min": 1400, "max": 2000, "rarity": "R", "icon": "🍌"}, 
    "31": {"name": "椰子", "cost": 800, "time": 122400, "min": 1500, "max": 2200, "rarity": "R", "icon": "🥥"}, 
    "32": {"name": "柠檬", "cost": 850, "time": 129600, "min": 1600, "max": 2400, "rarity": "R", "icon": "🍋"}, 
    "33": {"name": "老鼠尾草", "cost": 900, "time": 136800, "min": 1800, "max": 2600, "rarity": "R", "icon": "🐁"}, 
    "34": {"name": "三叶草", "cost": 950, "time": 144000, "min": 1900, "max": 2800, "rarity": "R", "icon": "☘️"}, 
    "35": {"name": "薰衣草", "cost": 1000, "time": 151200, "min": 2000, "max": 3000, "rarity": "R", "icon": "🪻"}, 

    # --- Level 3: 史诗区 (SR) ---
    "36": {"name": "极品猫薄荷", "cost": 2000, "time": 172800, "min": 4000, "max": 6000, "rarity": "SR", "icon": "🌿"}, 
    "37": {"name": "金枪鱼树", "cost": 2500, "time": 216000, "min": 5500, "max": 8000, "rarity": "SR", "icon": "🐟"}, 
    "38": {"name": "罐头花", "cost": 3000, "time": 259200, "min": 7000, "max": 10000, "rarity": "SR", "icon": "🥫"}, 
    "39": {"name": "激光笔果实", "cost": 3500, "time": 302400, "min": 8500, "max": 12000, "rarity": "SR", "icon": "🔴"}, 
    "40": {"name": "呼噜噜果", "cost": 4000, "time": 345600, "min": 10000, "max": 15000, "rarity": "SR", "icon": "💤"}, 
    "41": {"name": "水晶兰", "cost": 4500, "time": 388800, "min": 12000, "max": 18000, "rarity": "SR", "icon": "💠"}, 
    "42": {"name": "黄金麦穗", "cost": 5000, "time": 432000, "min": 14000, "max": 20000, "rarity": "SR", "icon": "🌾"}, 
    "43": {"name": "招财铜钱草", "cost": 5500, "time": 475200, "min": 16000, "max": 24000, "rarity": "SR", "icon": "💰"}, 
    "44": {"name": "彩虹棉花", "cost": 6000, "time": 518400, "min": 18000, "max": 28000, "rarity": "SR", "icon": "🌈"}, 
    "45": {"name": "翡翠竹", "cost": 6500, "time": 561600, "min": 20000, "max": 30000, "rarity": "SR", "icon": "🎋"}, 

    # --- Level 4: 传说区 (SSR) ---
    "46": {"name": "宝石玫瑰", "cost": 10000, "time": 604800, "min": 35000, "max": 50000, "rarity": "SSR", "icon": "🌹"}, 
    "47": {"name": "世界树幼苗", "cost": 20000, "time": 864000, "min": 75000, "max": 100000, "rarity": "SSR", "icon": "🌳"}, 
    "48": {"name": "星辰碎片", "cost": 30000, "time": 1209600, "min": 120000, "max": 160000, "rarity": "SSR", "icon": "✨"}, 
    "49": {"name": "喵神雕像", "cost": 50000, "time": 1814400, "min": 200000, "max": 300000, "rarity": "SSR", "icon": "🗽"}, 
    "50": {"name": "创世莲花", "cost": 100000, "time": 2592000, "min": 500000, "max": 800000, "rarity": "SSR", "icon": "🪷"}, 
}

def get_plant_by_name(name):
    # 支持模糊搜索 (可选) 或者精确匹配
    for pid, data in PLANTS.items():
        if data["name"] == name:
            return pid, data
    return None, None

def calculate_harvest(plant_id):
    """计算随机收益"""
    plant = PLANTS[plant_id]
    profit = random.randint(plant["min"], plant["max"])
    return profit