# MeowTown Bot

MeowTown 是一个以“猫咪小镇”为主题的 Discord Bot。  
当前版本已经整合了市民养成、农场、股市、大富翁、银行、娱乐城、犯罪中心、商店、背包、称号和排行榜等主要玩法。

## 玩法简介

- 市民系统：注册身份，生成名字、品种、花色和初始资金。
- 档案总控：通过 `/喵喵小镇 档案` 统一进入各个玩法面板。
- 农场系统：种植、收获、施肥、扩建和守卫。
- 股市系统：查看行情、买入卖出、融资还款、查看持仓。
- 大富翁系统：投骰子、买地、升级、收租、坐牢与保释。
- 银行系统：活期、定期、储户榜。
- 娱乐城系统：老虎机、2d6、21点、德州扑克、俄罗斯轮盘。
- 犯罪中心：打劫玩家、打劫银行、贿赂守卫、越狱对决。
- 商店与背包：购买和使用道具、配饰、娱乐城增益商品。
- 称号系统：抽取、收集、佩戴称号。
- 排行榜：查看资金榜和地产榜等排名。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env`：

```env
DISCORD_TOKEN=你的机器人Token
OWNER_IDS=123456789012345678,987654321098765432
```

说明：

- `DISCORD_TOKEN`：Discord Bot Token，必填。
- `OWNER_IDS`：Bot 管理员用户 ID，多个用英文逗号分隔。

### 3. 启动 Bot

```bash
python main.py
```

## 常用入口

- `/喵喵小镇 注册 [名字]`
- `/喵喵小镇 档案`
- `/喵喵小镇 帮助`

大部分玩法都已经收进“档案”面板按钮中，不再拆成很多独立命令。

## 项目主结构

```text
MeowTown/
├─ app/
│  ├─ cogs/
│  │  ├─ core/
│  │  └─ gameplay/
│  │     └─ casino/
│  ├─ db/
│  ├─ features/
│  └─ shared/
├─ data/
├─ docs/
├─ main.py
├─ README.MD
└─ requirements.txt
```

## 说明

- `app/cogs`：Discord 指令和交互面板入口。
- `app/db`：数据库建表、迁移和仓储访问。
- `app/features`：玩法规则和可复用业务逻辑。
- `app/shared`：帮助文案、静态数据和公共方法。

架构细节可以看：[docs/ARCHITECTURE.MD](D:/SillyTavern/dc%20bot制作/MeowTown/docs/ARCHITECTURE.MD)
