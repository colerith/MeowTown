import discord


HELP_DATA = {
	"🐱 市民中心 (基础)": {
		"icon": "🆔",
		"cmds": {
			"/市民 注册 [名字]": "【必做】办理入住手续，随机生成品种花色",
			"/市民 档案": "打开总控面板，统一进入股市、农场、大富翁、排行榜、商店、背包与称号",
			"/魔法屋 洗点": "花费喵币重塑你的品种和花色",
			"/改名卡": "使用改名卡修改昵称 (需在商店购买)",
		},
	},
	"🚜 喵喵农场 (挂机)": {
		"icon": "🌾",
		"cmds": {
			"/市民 档案 -> 农场": "打开农场主面板",
			"农场商店 / 收获 / 施肥 / 扩建": "都已整合进农场按钮打开的交互面板内",
		},
	},
	"📈 喵尔街股市 (博弈)": {
		"icon": "📊",
		"cmds": {
			"/市民 档案 -> 股市": "打开股市主面板",
			"买入 / 卖出 / 资产 / 融资": "都已整合进股市按钮打开的交互面板内",
		},
	},
	"🎲 喵喵大富翁 (冒险)": {
		"icon": "🏰",
		"cmds": {
			"/市民 档案 -> 大富翁": "打开大富翁主面板",
			"投骰子 / 买地 / 升级 / 道具 / 保释": "都已整合进大富翁按钮打开的交互面板内",
		},
	},
	"🛍️ 商业街 (消费)": {
		"icon": "👜",
		"cmds": {
			"/市民 档案 -> 商店": "打开商店购买面板",
			"/市民 档案 -> 背包": "查看和使用背包内物品",
		},
	},
	"👑 称号系统 (收集)": {
		"icon": "🏷️",
		"cmds": {
			"/市民 档案 -> 称号": "打开称号中心",
			"抽奖 / 佩戴 / 刷新": "都已整合进称号按钮打开的交互面板内",
		},
	},
}


def get_help_embed(bot_avatar_url):
	embed = discord.Embed(
		title="📜 喵喵小镇居民指南",
		description="欢迎来到喵喵小镇！这里是一个由猫咪主宰的模拟世界。\n以下是生存与致富的完全手册：",
		color=0xFFA500,
	)
	embed.set_thumbnail(url=bot_avatar_url)

	embed.add_field(
		name="🔰 新手三步走",
		value=(
			"1️⃣ **注册身份**：使用 `/市民 注册` 获得你的第一桶金。\n"
			"2️⃣ **打开总控**：使用 `/市民 档案`，从统一面板进入农场、股市和大富翁。\n"
			"3️⃣ **投资理财**：先靠农场和大富翁积累资金，再从档案面板进入股市搏一搏！"
		),
		inline=False,
	)

	for category, data in HELP_DATA.items():
		icon = data["icon"]
		content = ""
		for cmd, desc in data["cmds"].items():
			content += f"`{cmd}`\n└ {desc}\n"
		embed.add_field(name=f"{icon} {category}", value=content, inline=False)

	embed.set_footer(text="提示：大富翁破产会导致资产清算，股市融资需谨慎！ | Made with 🐱")
	return embed


__all__ = ["HELP_DATA", "get_help_embed"]
