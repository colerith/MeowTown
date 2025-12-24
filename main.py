# main.py
import discord
import os
import logging
import datetime
from dotenv import load_dotenv
from discord.ext import commands
from utils.db import setup_db

# --- 1. 配置日志系统 ---
# 设置日志格式：时间 - 级别 - 消息
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("喵喵小镇")

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

OWNER_IDS = [1353777207042113576] 

bot = discord.Bot(owner_ids=OWNER_IDS)

# --- 2. 启动时加载插件 ---
logger.info("--------------------------------------------------")
logger.info("🔄 正在启动插件加载程序...")

cogs_list = [
    f for f in os.listdir("./cogs") 
    if f.endswith(".py") and f != "__init__.py"
]

for filename in cogs_list:
    cog_name = f"cogs.{filename[:-3]}"
    try:
        bot.load_extension(cog_name)
        # ljust(15) 是为了让日志对齐更好看
        logger.info(f"✅ 加载插件成功: {filename[:-3].ljust(15)} | 状态: 正常")
    except Exception as e:
        logger.error(f"❌ 加载插件失败: {filename[:-3].ljust(15)} | 错误: {e}")

logger.info(f"📦 扫描到的插件总数: {len(cogs_list)}")
logger.info("--------------------------------------------------")

# --- 3. Bot 就绪事件 ---
@bot.event
async def on_ready():
    print("\n")
    logger.info("🟢 机器人已成功连接到 Discord 网关！")
    logger.info(f"🤖 当前登录用户: {bot.user} (ID: {bot.user.id})")
    logger.info(f"🌍 加入服务器数: {len(bot.guilds)} 个")
    logger.info(f"👑 管理员 ID:   {OWNER_IDS}")
    
    # 初始化数据库
    try:
        logger.info("💾 正在连接数据库...")
        await setup_db()
        logger.info("✅ 数据库连接成功，表结构已更新。")
    except Exception as e:
        logger.critical(f"🔥 数据库初始化失败: {e}")
        # 如果数据库挂了，Bot基本也没用了，可以选择退出
        # exit(1) 

    # 设置 Bot 的动态状态 (Activity)
    activity = discord.Game(name="/帮助 | 喵喵小镇 V1.0")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    
    logger.info("🚀 喵喵小镇机器人已完全就绪，开始提供服务！")
    print("\n")

# --- 4. 全局错误处理 (带详细堆栈) ---
@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    # 忽略命令未找到的错误
    if isinstance(error, commands.CommandNotFound):
        return

    # 处理权限检查失败 (CheckFailure)
    if isinstance(error, discord.errors.CheckFailure):
        await ctx.respond("🚫 **访问被拒绝**\n你还没有领养喵喵！请先使用 `/市民 注册` 办理入住手续。", ephemeral=True)
        logger.warning(f"⚠️  警告: 用户 {ctx.author} 尝试在未注册情况下使用命令 '{ctx.command.name}'")
    
    # 处理指令冷却 (Cooldown)
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.respond(f"⏳ 太快了！请等待 {error.retry_after:.1f} 秒后再试。", ephemeral=True)

    # 处理其他未预料的错误
    else:
        command_name = ctx.command.name if ctx.command else "未知命令"
        
        # 在控制台打印详细报错
        logger.error(f"❌ 执行命令 '/{command_name}' 时发生错误:")
        logger.error(f"   用户: {ctx.author} ({ctx.author.id})")
        logger.error(f"   异常信息: {error}", exc_info=True) # exc_info=True 会打印完整的报错代码行数
        
        try:
            await ctx.respond("💥 **系统错误**\n机器人遇到了一些问题，请联系管理员。", ephemeral=True)
        except:
            pass 

# 启动入口
if __name__ == "__main__":
    if not TOKEN:
        logger.critical("❌ 错误: 未在 .env 文件中找到 DISCORD_TOKEN！")
        exit(1)
    
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        logger.critical("❌ 错误: Discord Token 无效！请检查 .env 文件。")
    except Exception as e:
        logger.critical(f"❌ 启动时发生致命错误: {e}")