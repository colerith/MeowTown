# utils/stock_data.py
import random

# 股票定义（保持不变）
STOCKS = {
    "FISH": {"name": "咸鱼海运", "icon": "🐟", "base_price": 50, "volatility": 0.15},
    "CATN": {"name": "猫薄荷生物", "icon": "🌿", "base_price": 200, "volatility": 0.40},
    "TOY": {"name": "逗猫棒重工", "icon": "🎣", "base_price": 120, "volatility": 0.25},
    "BOX": {"name": "纸箱地产", "icon": "📦", "base_price": 80, "volatility": 0.10},
    "DOGE": {"name": "柴犬币", "icon": "🐕", "base_price": 10, "volatility": 0.90}
}

# --- 新闻组合部件 ---
NEWS_PARTS = {
    # [主语] 身份/机构 (中性)
    "subject": [
        {"text": "一位不愿透露姓名的太空公司CEO", "score": 0},
        {"text": "隔壁狗镇的贸易代表", "score": 0},
        {"text": "喵尔街的传奇投资人“喵菲特”", "score": 0},
        {"text": "一群环保主义猫", "score": 0},
        {"text": "小镇的网红主播", "score": 0},
        {"text": "喵喵议会的议员", "score": 0},
        {"text": "小镇银行的首席分析师", "score": 0},
        {"text": "喵喵大学的经济学教授", "score": 0},
        {"text": "黑帮大佬喵最信任的手下", "score": 0},
        {"text": "一群刚睡醒的幼猫", "score": 0},
        {"text": "一个神秘的时间旅行者", "score": 0},
        {"text": "喵尔街日报不负责任的记者", "score": 0},
        {"text": "一位普通的铲屎官", "score": 0},
        {"text": "小镇最受欢迎的兽医", "score": 0},
        {"text": "一个自称来自未来的机器人", "score": 0}
    ],
    # [动作] 评价/行为 (有利好/利空)
    "action": {
        "positive": [
            {"text": "公开赞扬了 {name} 的发展前景", "score": 1},
            {"text": "宣布大量买入 {name} 的股票", "score": 2},
            {"text": "发推表示“我爱 {name}”", "score": 3},
            {"text": "与 {name} 达成了战略合作协议", "score": 2},
            {"text": "预测其股价在下周将翻倍", "score": 1},
            {"text": "将其评为“年度最值得信赖品牌”", "score": 2},
            {"text": "在梦里梦到了 {name} 的股票代码并告诉了所有人", "score": 1},
            {"text": "表示其技术领先业界至少十年", "score": 2},
            {"text": "将其产品作为礼物送给了狗镇大使，促进了和平", "score": 1},
            {"text": "在小镇广场上为其举办了盛大的庆祝派对", "score": 1},
            {"text": "声称找到了 {name} 股价上涨的必胜公式", "score": 2},
            {"text": "将其加入了小镇的养老金投资组合", "score": 3},
            {"text": "为其创作了一首广为流传的赞美诗", "score": 1},
            {"text": "透露正在秘密研发与 {name} 相关的颠覆性产品", "score": 2},
            {"text": "宣布未来十年将只使用 {name} 的产品", "score": 2}
        ],
        "negative": [
            {"text": "警告称 {name} 存在巨大泡沫", "score": -2},
            {"text": "因产品质量问题公开起诉了 {name}", "score": -2},
            {"text": "宣布清仓其持有的所有 {name} 股票", "score": -3},
            {"text": "呼吁所有市民联合抵制 {name} 的产品", "score": -1},
            {"text": "发布了一份长达100页的做空报告", "score": -2},
            {"text": "称其CEO的猫德有亏，不值得信任", "score": -1},
            {"text": "发现其财务报表是用猫爪印画的，数据存疑", "score": -2},
            {"text": "将其从‘值得信赖’的供应商名单中移除", "score": -1},
            {"text": "公开嘲笑其过时的商业模式", "score": -1},
            {"text": "爆料其内部管理混乱，员工都在上班时间睡觉", "score": -2},
            {"text": "认为其技术毫无创新，是在“啃老本”", "score": -1},
            {"text": "发起了一项“30天不使用{name}”的网络挑战", "score": -1},
            {"text": "在小镇日报上刊登了整版的批评广告", "score": -2},
            {"text": "预测其将在下个月申请破产保护", "score": -3},
            {"text": "声称其产品会带来难以预料的厄运", "score": -1}
        ]
    },
    # [事件] 特定于某支股票的独立事件
    "event": {
        "FISH": [
            {"text": "捕获了一批极其罕见的深海金枪鱼", "score": 2},
            {"text": "的主力货船遭遇了海盗猫的突然袭击", "score": -3},
            {"text": "开辟了一条通往新渔场的黄金航线，渔获量大增", "score": 3},
            {"text": "因过度捕捞被海洋保护协会处以巨额罚款", "score": -2},
            {"text": "发明了永不腐坏的咸鱼干保鲜技术", "score": 2},
            {"text": "的船队在百慕大三角神秘失联了一整天", "score": -2},
            {"text": "与海鸥们达成了导航与反海盗战略合作", "score": 1},
            {"text": "的冷库系统发生故障，一半的鱼都变质了", "score": -3},
            {"text": "在一次深海探索中打捞到了古代沉船的宝藏", "score": 3},
            {"text": "的导航系统失灵，把一船鱼送到了大沙漠", "score": -1},
            {"text": "的船员因伙食太差宣布集体罢工", "score": -2},
            {"text": "新建造的旗舰“喵可波罗号”正式下水", "score": 2},
            {"text": "被一群虎鲸群盯上，被迫绕道行驶，成本大增", "score": -1},
            {"text": "的渔网被评为“年度最坚固发明”", "score": 1},
            {"text": "意外发现一片富含珍珠的牡蛎养殖场", "score": 2}
        ],
        "CATN": [
            {"text": "的最新研究发现猫薄荷能显著提升猫咪的数学能力", "score": 3},
            {"text": "的仓库发生神秘火灾，一半的库存化为灰烬", "score": -3},
            {"text": "成功合成了新品种“彩虹猫薄荷”，吸完能看见彩虹", "score": 2},
            {"text": "被曝出在产品中掺杂普通薄荷叶以次充好", "score": -2},
            {"text": "在月球上建立了首个太空猫薄荷种植基地", "score": 3},
            {"text": "的核心科学家带着机密配方跳槽去了隔壁狗镇", "score": -3},
            {"text": "提取出能产生绝对幸福感的“快乐素”，已申请专利", "score": 2},
            {"text": "的种植园被一群爱吃素的羊驼啃得一干二净", "score": -2},
            {"text": "成为了小镇官方指定的“情绪稳定供应商”", "score": 2},
            {"text": "的产品被指控会导致猫咪沉迷睡觉，无心工作", "score": -1},
            {"text": "的运输车队在路上发生泄漏，导致整条街的猫都嗨了", "score": 1},
            {"text": "因干旱天气导致今年的猫薄荷严重减产", "score": -2},
            {"text": "的猫薄荷味空气清新剂意外获得了狗群的喜爱，市场扩大", "score": 2},
            {"text": "被指控其种植园破坏了当地的生态环境", "score": -1},
            {"text": "宣布将与咸鱼海运合作，开拓海外市场", "score": 1}
        ],
        "TOY": [
            {"text": "推出了一款能和猫咪进行哲学辩论的智能逗猫棒", "score": 3},
            {"text": "的激光笔产品因安全隐患被勒令全球召回", "score": -2},
            {"text": "成为了年度“吸猫节”的独家玩具赞助商，品牌曝光度大增", "score": 2},
            {"text": "的核心设计专利被竞争对手“逗狗棒公司”抄袭", "score": -1},
            {"text": "在VR逗猫技术上取得革命性突破", "score": 2},
            {"text": "的生产线被一群调皮的猫咪占领，无法正常开工", "score": -2},
            {"text": "与知名动漫《进击的猫咪》达成IP联动", "score": 2},
            {"text": "因原材料羽毛价格上涨，生产成本急剧增加", "score": -1},
            {"text": "发明了永不断电的激光笔，备受好评", "score": 3},
            {"text": "CEO在产品发布会上演示产品时睡着了，引发市场担忧", "score": -2},
            {"text": "开发出能自动打扫猫毛的玩具老鼠，广受铲屎官欢迎", "score": 2},
            {"text": "的仓库被一群老鼠当成了游乐场，产品损坏严重", "score": -1},
            {"text": "的产品在海外市场意外大受欢迎", "score": 2},
            {"text": "被指控其玩具会让猫咪变得过度兴奋，影响邻里关系", "score": -1},
            {"text": "获得了“小镇最佳雇主”称号，员工士气高涨", "score": 1}
        ],
        "BOX": [
            {"text": "发明了冬暖夏凉还能自清洁的恒温纸箱，订单激增", "score": 3},
            {"text": "的纸箱被发现是“豆腐渣工程”，一碰就碎，信誉扫地", "score": -3},
            {"text": "收购了小镇所有的废品回收站，形成行业垄断", "score": 2},
            {"text": "的主要仓库遭遇了白蚁侵袭，损失惨重", "score": -2},
            {"text": "小镇通过了“一猫一箱”的住房保障法案", "score": 3},
            {"text": "一场突如其来的大雨淋湿了所有露天存放的纸箱", "score": -2},
            {"text": "发现了巨大的古代纸箱文明遗迹，引发考古热潮", "score": 1},
            {"text": "因胶带供应商突然倒闭，所有产品无法封箱发货", "score": -1},
            {"text": "其设计的“迷宫纸箱”获得了年度最佳设计奖", "score": 2},
            {"text": "被一群流浪狗当成了磨牙棒，客户投诉不断", "score": -1},
            {"text": "与逗猫棒重工合作，推出内置玩具的娱乐纸箱", "score": 1},
            {"text": "被环保组织抗议，指其浪费了过多的森林资源", "score": -1},
            {"text": "发明了可以折叠成任意形状的“变形纸箱”", "score": 2},
            {"text": "小镇开始流行睡塑料盆，纸箱的需求量有所下降", "score": -1},
            {"text": "获得了军方的大额订单，用于建造临时猫咪兵营", "score": 2}
        ],
        "DOGE": [
            {"text": "的图标被画在了一枚即将发射的火箭上，将登陆月球", "score": 4},
            {"text": "的创始人突然宣布删库跑路，留下一句“再见，傻瓜们”", "score": -5},
            {"text": "被小镇最火的咖啡店宣布接受为支付方式", "score": 3},
            {"text": "被发现其所谓的“区块链”网络其实由三只仓鼠在跑轮驱动", "score": -4},
            {"text": "一张极其可爱的柴犬新表情包在网络上病毒式传播", "score": 2},
            {"text": "被小镇银行行长公开斥责为“毫无价值的骗局”", "score": -3},
            {"text": "开发者宣布将销毁99%的供应量，造成通缩预期", "score": 4},
            {"text": "主要交易服务器的电线被一只路过的松鼠咬断了", "score": -2},
            {"text": "在一部热播科幻剧中被描绘成未来的宇宙通用货币", "score": 3},
            {"text": "被另一种动物币“哈士奇币”抢走了所有市场热度", "score": -3},
            {"text": "一位少年黑客声称找到了无限增发该币的漏洞", "score": -4},
            {"text": "社区发起投票，决定将图标换成一只猫，引发身份认同危机", "score": -1},
            {"text": "神秘代码显示其最终目标是解开宇宙的终极真理", "score": 2},
            {"text": "被发现其全部代码加起来只有一行注释：“汪汪汪！”", "score": -2},
            {"text": "没有任何理由，它就是突然涨了/跌了，因为它是柴犬币", "score": random.choice([-5, 5])}
        ]
    }
}

def generate_dynamic_news(stock_id):
    """
    动态生成一条新闻及其综合情绪分
    返回: (news_text, total_score)
    """
    stock_name = STOCKS[stock_id]["name"]
    
    # 60%概率是特定事件，40%是通用评价
    if random.random() < 0.6:
        # 单独的股票特定事件
        event_part = random.choice(NEWS_PARTS["event"][stock_id])
        news_text = f"据喵尔街日报报道，{stock_name} {event_part['text']}。"
        total_score = event_part["score"]
    else:
        # 拼接通用新闻: [主语] + [动作]
        subject_part = random.choice(NEWS_PARTS["subject"])
        trend = "positive" if random.random() < 0.5 else "negative"
        action_part = random.choice(NEWS_PARTS["action"][trend])
        
        news_text = subject_part["text"] + " " + action_part["text"].format(name=stock_name)
        total_score = subject_part["score"] + action_part["score"]
        
    return news_text, total_score