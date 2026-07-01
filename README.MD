# MeowTown Bot

MeowTown 是一个以“猫咪小镇”为主题的 Discord Bot，提供注册养成、农场挂机、股市交易、大富翁、商店道具、称号收集和排行榜等玩法。

项目目前已经完成主要目录重构，代码按 `cogs / features / db / shared` 分层组织，方便继续扩展功能和维护。

详细架构说明见：[docs/ARCHITECTURE.MD](D:/SillyTavern/dc%20bot制作/MeowTown/docs/ARCHITECTURE.MD)

## 功能简介

- 市民系统：注册猫咪身份，生成名字、品种、花色与初始资金。
- 农场系统：种植、收获、扩建、偷菜、使用农场道具。
- 股市系统：查看行情、买入卖出、融资还款、查看投资组合。
- 大富翁系统：投骰子移动、买地、升级、收租、使用道具、坐牢与保释。
- 商店与背包：购买功能道具、配饰、改名卡等，并在背包中使用。
- 称号系统：抽取称号、收集称号、佩戴展示。
- 排行榜：查看资产榜、地产榜等排名。
- 管理与通用命令：基础帮助、Bot 管理类命令。

## 技术栈

- Python 3.11+
- [py-cord](https://docs.pycord.dev/)
- `aiosqlite`
- `python-dotenv`

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
DISCORD_TOKEN=你的机器人Token
OWNER_IDS=123456789012345678,987654321098765432
```

说明：

- `DISCORD_TOKEN`：Discord Bot Token，必填。
- `OWNER_IDS`：Bot 管理员用户 ID，多个用英文逗号分隔；不填时会使用代码中的默认值。

### 3. 启动 Bot

```bash
python main.py
```

启动入口：

- [main.py](D:/SillyTavern/dc%20bot制作/MeowTown/main.py)
- [app/bootstrap.py](D:/SillyTavern/dc%20bot制作/MeowTown/app/bootstrap.py)

## 项目结构

当前项目主结构如下：

```text
MeowTown/
├─ app/
│  ├─ bootstrap.py
│  ├─ config/
│  │  └─ settings.py
│  ├─ core/
│  │  ├─ bot.py
│  │  ├─ lifecycle.py
│  │  └─ loader.py
│  ├─ cogs/
│  │  ├─ core/
│  │  │  ├─ admin.py
│  │  │  └─ general.py
│  │  └─ gameplay/
│  │     ├─ cat.py
│  │     ├─ farm.py
│  │     ├─ monopoly.py
│  │     ├─ ranking.py
│  │     ├─ shop.py
│  │     ├─ stock_market.py
│  │     └─ title.py
│  ├─ db/
│  │  ├─ engine.py
│  │  └─ repositories/
│  │     ├─ farm_repo.py
│  │     ├─ inventory_repo.py
│  │     ├─ monopoly_repo.py
│  │     ├─ ranking_repo.py
│  │     ├─ stock_repo.py
│  │     ├─ title_repo.py
│  │     └─ user_repo.py
│  ├─ features/
│  │  ├─ monopoly/
│  │  │  └─ service.py
│  │  ├─ profile/
│  │  │  ├─ cog.py
│  │  │  ├─ repository.py
│  │  │  ├─ service.py
│  │  │  └─ ui/
│  │  │     ├─ modals.py
│  │  │     └─ views.py
│  │  └─ stock_market/
│  │     └─ service.py
│  ├─ shared/
│  │  ├─ checks.py
│  │  ├─ constants.py
│  │  ├─ helpers.py
│  │  └─ data/
│  │     ├─ cat_data.py
│  │     ├─ farm_data.py
│  │     ├─ map_data.py
│  │     ├─ shop_data.py
│  │     ├─ stock_data.py
│  │     └─ title_data.py
│  └─ ui/
│     └─ components/
├─ data/
├─ docs/
│  └─ ARCHITECTURE.MD
├─ tests/
│  ├─ test_feature_services.py
│  └─ test_repositories.py
├─ .env
├─ .gitignore
├─ main.py
├─ README.MD
└─ requirements.txt
```

## 目录说明

- `app/core`：Bot 初始化、日志、生命周期、扩展加载。
- `app/cogs`：Discord 命令入口层。
- `app/features`：按功能聚合的业务逻辑与专属 UI。
- `app/db`：数据库初始化与仓储层。
- `app/shared`：公共检查器、帮助方法、静态数据。
- `tests`：仓储集成测试与 service 单元测试。
- `docs`：架构与迁移说明文档。

## 运行机制

- 启动时由 [app/core/loader.py](D:/SillyTavern/dc%20bot制作/MeowTown/app/core/loader.py) 自动扫描并加载 `app/cogs/**` 下的扩展。
- 数据库由 [app/db/engine.py](D:/SillyTavern/dc%20bot制作/MeowTown/app/db/engine.py) 负责建表与迁移。
- 主要数据访问通过 `app/db/repositories/` 统一收口。
- 一部分纯业务规则已经下沉到 `app/features/*/service.py`，用于减少 Cog 体积并提升可测试性。

## 测试

当前已补齐首批核心测试，包含：

- repository 集成测试：
  - `user_repo`
  - `farm_repo`
  - `inventory_repo`
  - `title_repo`
  - `ranking_repo`
  - `stock_repo`
  - `monopoly_repo`
  - `app/features/profile/repository.py`
- service 单元测试：
  - `app/features/profile/service.py`
  - `app/features/monopoly/service.py`
  - `app/features/stock_market/service.py`

运行测试：

```bash
python -m unittest -v
```

## 开发说明

- 新功能优先放到 `app/*` 新结构中，不再恢复旧路径写法。
- SQL 不直接写在 Cog 中，统一通过 repository 或 feature repository 处理。
- 纯业务逻辑优先沉到 `service.py`，便于补测试和后续维护。

## 后续方向

- 继续将 `cat / farm / shop / title` 中可抽离的规则迁移到 `app/features/*/service.py`。
- 继续补交互层和启动层的最小回归测试。
- 持续保持 README 与架构文档同步。
