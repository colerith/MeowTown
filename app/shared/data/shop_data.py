# 商品定义
# type: tool(道具), farm(农场), cosmetic(装饰)
SHOP_ITEMS = {
    # --- 道具类 ---
    "遥控骰子": {"name": "遥控骰子", "price": 2000, "type": "tool", "desc": "大富翁：下一次投掷必定指定点数", "icon": "🎲"},
    "路障": {"name": "路障", "price": 1000, "type": "tool", "desc": "大富翁：放置在当前地产，过路费翻倍", "icon": "🚧"},
    "改名卡": {"name": "改名卡", "type": "tool", "price": 5000, "desc": "修改你的市民昵称", "icon": "💳"},
    "保释卡": {"name": "保释卡", "type": "tool", "price": 1000, "desc": "大富翁：免除一次牢狱之灾", "icon": "🕊️"},
    "打劫防护盾": {
        "name": "打劫防护盾",
        "price": 5000,
        "type": "buff",
        "desc": "娱乐城：5小时内被打劫成功率降低 30%",
        "icon": "🛡️",
        "buff_type": "rob_protection",
        "duration_hours": 5,
        "daily_limit": 5,
    },
    "初级好运符": {
        "name": "初级好运符",
        "price": 2500,
        "type": "buff",
        "desc": "娱乐城：1小时内赌博获胜奖金提高 5%",
        "icon": "🍀",
        "buff_type": "good_luck",
        "duration_hours": 1,
        "daily_limit": 10,
    },
    "筹码校准器": {
        "name": "筹码校准器",
        "price": 3000,
        "type": "tool",
        "desc": "娱乐城：使用后 2 小时内赌博获胜奖金再提高 20%",
        "icon": "🎛️",
        "effect_type": "casino_focus",
        "duration_hours": 2,
    },
    "皇家赌约": {
        "name": "皇家赌约",
        "price": 20000,
        "type": "buff",
        "desc": "娱乐城：30分钟内赌博获胜奖金提高 15%",
        "icon": "👑",
        "buff_type": "super_luck",
        "duration_hours": 0.5,
        "daily_limit": 2,
    },

    # --- 农场类 ---
    "小包催熟粉": {"name": "小包催熟粉", "type": "farm", "price": 120, "desc": "农场：立刻减少所有作物 10分钟 生长时间", "icon": "🧂"},
    "金坷垃": {"name": "金坷垃", "type": "farm", "price": 500, "desc": "农场：立刻减少所有作物 1小时 生长时间", "icon": "🧪"},
    "超级金坷垃": {"name": "超级金坷垃", "type": "farm", "price": 1500, "desc": "农场：立刻减少所有作物 5小时 生长时间", "icon": "💉"},
    "火箭燃素": {"name": "火箭燃素", "type": "farm", "price": 3200, "desc": "农场：立刻减少所有作物 12小时 生长时间", "icon": "🚀"},

    # --- 装饰类 (穿戴后显示在档案上) ---
    "墨镜": {"name": "墨镜", "type": "cosmetic", "price": 800, "desc": "装饰：酷酷的感觉", "icon": "🕶️"},
    "蝴蝶结": {"name": "蝴蝶结", "type": "cosmetic", "price": 800, "desc": "装饰：可可爱爱", "icon": "🎀"},
    "金项链": {"name": "金项链", "type": "cosmetic", "price": 5000, "desc": "装饰：土豪的象征", "icon": "🥇"},
    "皇冠": {"name": "皇冠", "type": "cosmetic", "price": 50000, "desc": "装饰：王者的荣耀", "icon": "👑"},
    "圣诞帽": {"name": "圣诞帽", "type": "cosmetic", "price": 1200, "desc": "装饰：节日限定", "icon": "🎅"},
    "耳机": {"name": "耳机", "type": "cosmetic", "price": 1000, "desc": "装饰：动感十足", "icon": "🎧"},
}
