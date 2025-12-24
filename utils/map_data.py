# utils/map_data.py
import random

# --- 游戏核心参数 ---
MAP_SIZE = 50
PASS_GO_SALARY = 2000
BAIL_COST = 1500

# --- 地图定义 (50个地块) ---
# 地产租金格式: [Lv.1, Lv.2, Lv.3, Lv.4, Lv.5]
MAP = [
    {"id": 0, "type": "start", "name": "小镇起点", "icon": "🏁"},
    {"id": 1, "type": "property", "name": "猫砂盆社区", "price": 600, "rent": [50, 150, 450, 800, 1200], "icon": "🛖", "color": "Brown"},
    {"id": 2, "type": "chance", "name": "机会", "icon": "❓"},
    {"id": 3, "type": "property", "name": "毛线球乐园", "price": 800, "rent": [60, 180, 540, 950, 1400], "icon": "🧶", "color": "Brown"},
    {"id": 4, "type": "tax", "name": "消费税", "fee": 1000, "icon": "💸"},
    {"id": 5, "type": "property", "name": "鱼骨天桥", "price": 1200, "rent": [80, 240, 720, 1260, 1800], "icon": "🌉", "color": "LightBlue"},
    {"id": 6, "type": "destiny", "name": "命运", "icon": "📜"},
    {"id": 7, "type": "property", "name": "纸箱公寓", "price": 1200, "rent": [80, 240, 720, 1260, 1800], "icon": "📦", "color": "LightBlue"},
    {"id": 8, "type": "property", "name": "猫薄荷花园", "price": 1500, "rent": [100, 300, 900, 1600, 2500], "icon": "🌿", "color": "LightBlue"},
    {"id": 9, "type": "plaza", "name": "中心广场", "icon": "⛲"},
    
    {"id": 10, "type": "jail", "name": "禁闭室 (仅探望)", "icon": "👮"},
    {"id": 11, "type": "property", "name": "猫爪步道", "price": 1800, "rent": [120, 360, 1000, 1800, 2800], "icon": "🐾", "color": "Pink"},
    {"id": 12, "type": "chance", "name": "机会", "icon": "❓"},
    {"id": 13, "type": "property", "name": "呼噜声沙龙", "price": 1800, "rent": [120, 360, 1000, 1800, 2800], "icon": "💈", "color": "Pink"},
    {"id": 14, "type": "property", "name": "喵呜大道", "price": 2200, "rent": [150, 450, 1250, 2200, 3200], "icon": "🛣️", "color": "Pink"},
    {"id": 15, "type": "property", "name": "金枪鱼市场", "price": 2500, "rent": [200, 600, 1800, 3200, 4500], "icon": "🐟", "color": "Orange"},
    {"id": 16, "type": "destiny", "name": "命运", "icon": "📜"},
    {"id": 17, "type": "property", "name": "三文鱼溪", "price": 2500, "rent": [200, 600, 1800, 3200, 4500], "icon": "🏞️", "color": "Orange"},
    {"id": 18, "type": "property", "name": "沙丁鱼广场", "price": 2800, "rent": [220, 660, 2000, 3500, 5000], "icon": "🏦", "color": "Orange"},
    {"id": 19, "type": "plaza", "name": "喷泉花园", "icon": "⛲"},

    {"id": 20, "type": "property", "name": "红点激光馆", "price": 3200, "rent": [250, 750, 2250, 4000, 5500], "icon": "🔴", "color": "Red"},
    {"id": 21, "type": "chance", "name": "机会", "icon": "❓"},
    {"id": 22, "type": "property", "name": "逗猫棒工厂", "price": 3200, "rent": [250, 750, 2250, 4000, 5500], "icon": "🏭", "color": "Red"},
    {"id": 23, "type": "property", "name": "羽毛棒作坊", "price": 3500, "rent": [280, 840, 2500, 4500, 6200], "icon": "🪶", "color": "Red"},
    {"id": 24, "type": "property", "name": "黄金鱼骨", "price": 3800, "rent": [300, 900, 2700, 4800, 6800], "icon": "⚜️", "color": "Yellow"},
    {"id": 25, "type": "destiny", "name": "命运", "icon": "📜"},
    {"id": 26, "type": "property", "name": "钻石项圈店", "price": 3800, "rent": [300, 900, 2700, 4800, 6800], "icon": "💎", "color": "Yellow"},
    {"id": 27, "type": "property", "name": "猫薄荷交易所", "price": 4200, "rent": [330, 1000, 3000, 5200, 7500], "icon": "💹", "color": "Yellow"},
    {"id": 28, "type": "tax", "name": "奢侈品税", "fee": 2500, "icon": "💸"},
    {"id": 29, "type": "property", "name": "罐头加工厂", "price": 4500, "rent": [360, 1100, 3300, 5600, 8000], "icon": "🥫", "color": "Green"},

    {"id": 30, "type": "go_to_jail", "name": "👮‍➡️ 坏事了！", "icon": "🚓"},
    {"id": 31, "type": "property", "name": "私猫侦探社", "price": 4500, "rent": [360, 1100, 3300, 5600, 8000], "icon": "🕵️", "color": "Green"},
    {"id": 32, "type": "chance", "name": "机会", "icon": "❓"},
    {"id": 33, "type": "property", "name": "魔法屋", "price": 4800, "rent": [390, 1200, 3600, 6000, 8500], "icon": "🔮", "color": "Green"},
    {"id": 34, "type": "destiny", "name": "命运", "icon": "📜"},
    {"id": 35, "type": "property", "name": "小镇电视台", "price": 5200, "rent": [420, 1300, 3900, 6500, 9200], "icon": "📺", "color": "DarkBlue"},
    {"id": 36, "type": "chance", "name": "机会", "icon": "❓"},
    {"id": 37, "type": "property", "name": "喵喵摩天楼", "price": 5500, "rent": [450, 1400, 4200, 7000, 10000], "icon": "🏙️", "color": "DarkBlue"},
    {"id": 38, "type": "property", "name": "市长庄园", "price": 6000, "rent": [500, 1500, 4500, 7500, 11000], "icon": "🏰", "color": "DarkBlue"},
    {"id": 39, "type": "plaza", "name": "皇家花园", "icon": "⛲"},

    {"id": 40, "type": "property", "name": "太空电梯", "price": 7000, "rent": [600, 1800, 5400, 9000, 13000], "icon": "🛰️", "color": "Purple"},
    {"id": 41, "type": "destiny", "name": "命运", "icon": "📜"},
    {"id": 42, "type": "property", "name": "月球基地", "price": 7500, "rent": [650, 2000, 6000, 10000, 15000], "icon": "🌕", "color": "Purple"},
    {"id": 43, "type": "chance", "name": "机会", "icon": "❓"},
    {"id": 44, "type": "property", "name": "银河系商会", "price": 8000, "rent": [700, 2200, 6600, 11000, 16000], "icon": "🌌", "color": "Purple"},
    {"id": 45, "type": "destiny", "name": "命运", "icon": "📜"},
    {"id": 46, "type": "property", "name": "喵星议会", "price": 9000, "rent": [800, 2500, 7500, 12500, 18000], "icon": "🏛️", "color": "Gold"},
    {"id": 47, "type": "chance", "name": "机会", "icon": "❓"},
    {"id": 48, "type": "property", "name": "时间机器", "price": 10000, "rent": [1000, 3000, 9000, 15000, 22000], "icon": "⏳", "color": "Gold"},
    {"id": 49, "type": "property", "name": "创世之爪", "price": 12000, "rent": [1200, 3600, 10800, 18000, 26000], "icon": "🐾", "color": "Gold"}
]

# --- 随机事件卡库 (100个) ---
EVENT_CARDS = {
    "chance": [
        # 金钱 - 正面
        {"text": "你在公园捡到了一个装满小鱼干的钱包，卖掉后赚了 2000 喵币。", "type": "money", "value": 2000},
        {"text": "灵感爆发！你设计的猫抓板获得了年度大奖，获得 5000 喵币奖金。", "type": "money", "value": 5000},
        {"text": "你中了一张彩票！获得 10000 喵币！", "type": "money", "value": 10000},
        {"text": "银行系统出错，你的账户里凭空多了 1500 喵币。", "type": "money", "value": 1500},
        {"text": "你主演的猫咪视频火了，获得广告分成 3000 喵币。", "type": "money", "value": 3000},
        {"text": "你找到了一个隐藏的古代猫粮宝库，获得 7500 喵币。", "type": "money", "value": 7500},
        {"text": "你投资的柴犬币突然暴涨，净赚 4000 喵币。", "type": "money", "value": 4000},
        {"text": "你将自己的打呼噜声录制成白噪音，版权费收入 1000 喵币。", "type": "money", "value": 1000},
        {"text": "税务局退税，你收到了 2500 喵币。", "type": "money", "value": 2500},
        {"text": "你作为模特拍摄的猫爪照片大受欢迎，获得 3500 喵币报酬。", "type": "money", "value": 3500},
        {"text": "你因可爱的外表被评为“小镇吉祥物”，获得政府奖励 6000 喵币。", "type": "money", "value": 6000},
        {"text": "你卖掉了自己掉的毛，一位艺术家用它们做了个雕塑，你赚了500喵币。", "type": "money", "value": 500},
        {"text": "你清理沙发底下时发现了一些被遗忘的私房钱，共 1200 喵币。", "type": "money", "value": 1200},
        {"text": "你破解了一个宇宙难题，获得诺贝尔喵学奖，奖金 20000 喵币。", "type": "money", "value": 20000},
        {"text": "银行的利息结算了，你获得 1800 喵币。", "type": "money", "value": 1800},
        # 金钱 - 负面
        {"text": "走路玩手机，不小心踩到香蕉皮，摔进了医院，支付 800 喵币医药费。", "type": "money", "value": -800},
        {"text": "你买的限量版猫抓板是假货，损失了 1000 喵币。", "type": "money", "value": -1000},
        {"text": "你打碎了邻居家的祖传花瓶，赔偿 3000 喵币。", "type": "money", "value": -3000},
        {"text": "你试图偷吃桌上的小鱼干，结果把桌子弄翻了，修理费 1500 喵币。", "type": "money", "value": -1500},
        {"text": "你的年度体检报告出来了，需要支付 2000 喵币的检查费。", "type": "money", "value": -2000},
        {"text": "你沉迷于网络游戏，不小心氪金了 4000 喵币。", "type": "money", "value": -4000},
        {"text": "你被一只蚊子叮了，买药膏花了 200 喵币。", "type": "money", "value": -200},
        {"text": "你忘记缴纳水电费，被罚款 500 喵币。", "type": "money", "value": -500},
        {"text": "你向黑帮大佬喵借的钱到期了，支付 2500 喵币利息。", "type": "money", "value": -2500},
        {"text": "你看上了一个超级豪华的猫窝，冲动消费了 6000 喵币。", "type": "money", "value": -6000},
        # 移动
        {"text": "一阵狂风吹过，你前进 3 格。", "type": "move", "value": 3},
        {"text": "你跳上了一辆飞驰的快递车，被带到了 5 格之后的地方。", "type": "move", "value": 5},
        {"text": "你被一个好闻的气味吸引，后退了 2 格去寻找源头。", "type": "move", "value": -2},
        {"text": "你追着自己的尾巴转圈，把自己转晕了，停在原地。", "type": "move", "value": 0},
        {"text": "快去看！中心广场有免费小鱼干！", "type": "move_to", "value": 9},
        {"text": "你被一道神秘的光束传送到了喵喵摩天楼。", "type": "move_to", "value": 37},
        {"text": "你迷路了，直接回到起点重新开始吧。", "type": "move_to", "value": 0},
        {"text": "你闻到了禁闭室的饭香，决定去探望一下。", "type": "move_to", "value": 10},
        {"text": "你搭上了一班特快列车，直接前进 10 格！", "type": "move", "value": 10},
        {"text": "你走错路了，向后移动 4 格。", "type": "move", "value": -4},
        # 特殊
        {"text": "坏了，你被发现偷看隔壁小猫洗澡，快进禁闭室！", "type": "go_to_jail"},
        {"text": "你捡到了一张“出狱许可证”！好好保管。", "type": "item", "value": "出狱许可证"},
        {"text": "你参加社区大扫除，表现出色，获得荣誉市民称号。", "type": "nothing"},
        {"text": "你睡了一个完美的午觉，精力充沛。", "type": "nothing"},
        {"text": "今天天气真好，你在草地上打了个滚。", "type": "nothing"},
        {"text": "你获得了一次免费升级机会！如果停在自己的地产上，可免费升一级。", "type": "free_upgrade"},
        {"text": "你被任命为下一回合的税务官，可以向下一位踩到你地产的玩家收取双倍租金。", "type": "double_rent"},
        {"text": "你发现了一个虫洞，可以立即传送到地图上的任意一个“机会”或“命运”地块。", "type": "teleport_special"},
        {"text": "你发明了一个“万能遥控器”，可以决定下一次骰子的点数。", "type": "item", "value": "遥控骰子"},
        {"text": "“滚出我的地盘！”你获得了一张可以强制驱逐某个地块上的玩家的“驱逐令”。", "type": "item", "value": "驱逐令"},
        {"text": "你获得了一份地产蓝图，下次购买地产时可以打八折。", "type": "discount_purchase"},
        {"text": "你获得了一张“建筑许可证”，下次升级建筑时费用减半。", "type": "discount_upgrade"},
        {"text": "你被市长任命为交通协管员，原地停留一回合。", "type": "skip_turn"},
        {"text": "你捡到了一张“均富卡”，可以选择一位玩家，平分你们俩的现金。", "type": "equalize_cash"},
        {"text": "你获得了一张“抢夺卡”，可以随机抢走一位玩家的一处地产！(最便宜的)", "type": "steal_property"},
    ],
    "destiny": [
        # 金钱 - 正面
        {"text": "你继承了一笔远房亲戚的遗产，获得 8000 喵币！", "type": "money", "value": 8000},
        {"text": "今天是你的生日！银行送了你 3000 喵币的红包。", "type": "money", "value": 3000},
        {"text": "你发表的喵学论文被评为年度最佳，获得科研奖金 5000 喵币。", "type": "money", "value": 5000},
        {"text": "你投资的房地产升值了，获得 4500 喵币。", "type": "money", "value": 4500},
        {"text": "你扶了一位老奶奶猫过马路，她给了你 1000 喵币作为感谢。", "type": "money", "value": 1000},
        {"text": "你在街头卖艺，高超的钻箱子技巧为你赢得了 2000 喵币打赏。", "type": "money", "value": 2000},
        {"text": "你起诉了“逗狗棒公司”抄袭，打赢了官司，获得赔偿 12000 喵币。", "type": "money", "value": 12000},
        {"text": "你成为了“猫抓板月度会员”，收到了返现 500 喵币。", "type": "money", "value": 500},
        {"text": "你在年度猫咪选美大赛中获胜，奖金 15000 喵币。", "type": "money", "value": 15000},
        {"text": "你在阁楼里发现了一幅名画《蒙娜丽喵的微笑》，拍卖后获得 25000 喵币。", "type": "money", "value": 25000},
        {"text": "你为小镇的孤儿院捐款，市长授予你荣誉勋章和 2000 喵币奖励。", "type": "money", "value": 2000},
        {"text": "你参加大胃王比赛，赢得了冠军和终身免费小鱼干（折现 3000 喵币）。", "type": "money", "value": 3000},
        {"text": "你的储蓄罐满了，一共存了 2200 喵币。", "type": "money", "value": 2200},
        {"text": "一位神秘富豪随机挑选了你作为幸运儿，赠予你 9999 喵币。", "type": "money", "value": 9999},
        {"text": "你在后院挖出了石油，一夜暴富！获得 50000 喵币！", "type": "money", "value": 50000},
        # 金钱 - 负面
        {"text": "你的猫窝需要装修，花费 1500 喵币。", "type": "money", "value": -1500},
        {"text": "因为随地大小便，被城市管理员罚款 500 喵币。", "type": "money", "value": -500},
        {"text": "你超速飞行被开罚单，罚款 1000 喵币。", "type": "money", "value": -1000},
        {"text": "你吐出的毛球堵塞了市政下水道，支付疏通费 2200 喵币。", "type": "money", "value": -2200},
        {"text": "你需要为你所有的地产缴纳本年度的房产税，共 4000 喵币。", "type": "money", "value": -4000},
        {"text": "你参加慈善晚宴，捐出了 3000 喵币。", "type": "money", "value": -3000},
        {"text": "你看牙医，补牙花了 1800 喵币。", "type": "money", "value": -1800},
        {"text": "你买的猫粮过期了，全部扔掉，损失 600 喵币。", "type": "money", "value": -600},
        {"text": "你试图“黑”进银行系统，被发现并罚款 5000 喵币。", "type": "money", "value": -5000},
        {"text": "你家里的沙发被你抓坏了，买新的花了 3500 喵币。", "type": "money", "value": -3500},
        # 移动
        {"text": "你被一道神秘的光击中，后退 5 格！", "type": "move", "value": -5},
        {"text": "你闻到了一股无法抗拒的猫薄荷香味，前进 4 格。", "type": "move", "value": 4},
        {"text": "你被选中参加太空任务，直接前往月球基地！", "type": "move_to", "value": 42},
        {"text": "直接前往起点，领取你的薪水！", "type": "move_to", "value": 0},
        {"text": "你收到了市长庄园的派对邀请函，立即前往！", "type": "move_to", "value": 38},
        {"text": "糟糕，你走到了地图的边缘，被弹回了 3 格。", "type": "move", "value": -3},
        {"text": "你找到了一条捷径，前进 6 格。", "type": "move", "value": 6},
        {"text": "你被一个飞盘吸引，跟着它跑到了地图的随机一个位置。", "type": "move_random"},
        {"text": "你的GPS坏了，向后移动直到下一个“命运”或“机会”格。", "type": "move_to_special"},
        {"text": "你决定去最近的广场上晒太阳。", "type": "move_to_type", "value": "plaza"},
        # 特殊
        {"text": "你的所有地产都需要进行安全检查，为每处地产支付 500 喵币。", "type": "pay_per_property", "value": 500},
        {"text": "城市发展！你的所有地产集体升值，每处地产为你带来 1000 喵币的收益。", "type": "gain_per_property", "value": 1000},
        {"text": "今天是你所在街区的“邻里日”，和你最近的玩家交换位置。", "type": "swap_position"},
        {"text": "你获得了“地产大亨”的祝福，接下来三次支付租金减半。", "type": "rent_halved"},
        {"text": "一场灾难降临，随机摧毁了地图上一处建筑的最高一级。（可能是你的，也可能是别人的）", "type": "downgrade_random"},
        {"text": "你捡到了一张“路障”，可以放置在你的地产上，使下次过路费翻倍。", "type": "item", "value": "路障"},
        {"text": "你帮助了魔法屋的巫师，他给了你一张“传送门”，可以移动到地图上任意一处地产。", "type": "teleport_property"},
        {"text": "“今天我买单！”你必须替全地图上所有玩家支付他们下次踩到的税款。", "type": "pay_tax_for_all"},
        {"text": "你获得了“黑市执照”，可以强制以8折的价格收购一块无人拥有的土地。", "type": "item", "value": "黑市执照"},
        {"text": "你获得了“建筑豁免权”，可以无视规则，在任意一块自己的土地上再升一级（突破5级上限，变为地标！）", "type": "landmark_upgrade"},
        {"text": "你被卷入了时空裂缝，与地图上最富有/最贫穷的玩家交换了所有现金！", "type": "swap_cash_extreme"},
        {"text": "你对一位玩家使用了“喵之凝视”，该玩家下一回合无法投骰子。", "type": "freeze_player"},
        {"text": "你获得了“保险单”，下次因负面事件损失金钱时，可以免除损失。", "type": "item", "value": "保险单"},
        {"text": "你发起了一场“地产拍卖会”，随机选择一块无人拥有的土地，所有玩家都可以参与竞拍。", "type": "auction"},
        {"text": "命运的抉择：你可以选择获得 5000 喵币，或者让随机一位其他玩家损失 10000 喵币。", "type": "choice_money"},
    ]
}

def get_map_tile(position):
    """根据位置ID获取地块信息"""
    safe_position = position % MAP_SIZE
    return MAP[safe_position]

def get_random_event(card_type):
    """随机抽取一张事件卡"""
    if card_type in EVENT_CARDS:
        return random.choice(EVENT_CARDS[card_type])
    return None

def is_bad_event(event):
    """判断是否为倒霉事件"""
    if not event: return False
    # 扣钱、进监狱、按房产扣钱
    if event['type'] == 'money' and event['value'] < 0: return True
    if event['type'] == 'go_to_jail': return True
    if event['type'] == 'pay_per_property': return True
    if event['type'] == 'tax': return True # 虽然tax不是卡片，但逻辑通用
    return False

def get_guaranteed_good_event(card_type):
    """强制抽取一张好卡（保底用）"""
    if card_type not in EVENT_CARDS: return None
    
    good_cards = [
        e for e in EVENT_CARDS[card_type] 
        if (e['type'] == 'money' and event_value_safe(e) >= 2000) 
        or e['type'] == 'item'
        or e['type'] == 'gain_per_property'
    ]
    
    if good_cards:
        return random.choice(good_cards)
    return random.choice(EVENT_CARDS[card_type])

def event_value_safe(event):
    """辅助读取 value，防止没有 value 字段报错"""
    return event.get('value', 0)