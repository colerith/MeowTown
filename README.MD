# MeowTown Bot 重构规划（目录拆分版）

本 README 先定义**目标目录结构**与**拆分迁移计划**，方便后续逐步重构。

当前目标是把你提到的内容归位：
- UI 相关放一起
- init/启动与配置放一起
- 核心 Cog 放一起
- DB 访问层放一起
- 各功能模块按领域拆包

---

## 1. 当前结构（简化）

```text
MeowTown/
├─ main.py
├─ requirements.txt
├─ cogs/
│  ├─ admin.py
│  ├─ cat.py
│  ├─ farm.py
│  ├─ general.py
│  ├─ monopoly.py
│  ├─ ranking.py
│  ├─ shop.py
│  ├─ stock_market.py
│  ├─ title.py
│  ├─ core/
│  │  └─ database.py
│  └─ modules/
│     └─ profile/
│        ├─ __init__.py
│        ├─ cog.py
│        ├─ data.py
│        ├─ database.py
│        └─ ui.py
└─ utils/
	├─ cat_data.py
	├─ farm_data.py
	├─ map_data.py
	├─ shop_data.py
	├─ stock_data.py
	├─ title_data.py
	├─ checks.py
	├─ db.py
	└─ helpers.py
```

问题点：
- `cogs/`、`cogs/modules/`、`utils/` 职责有交叉（业务逻辑、数据、DB、UI 混在不同层级）。
- `core/database.py` 与 `utils/db.py` 可能重复职责。
- 功能模块（cat/farm/shop/title 等）尚未统一成“模块包”形态。

---

## 2. 目标结构（建议）

```text
MeowTown/
├─ app/
│  ├─ __init__.py
│  ├─ bootstrap.py                # 启动入口（原 main.py 逻辑拆过来）
│  ├─ config/
│  │  ├─ __init__.py
│  │  └─ settings.py              # token、前缀、环境变量读取
│  ├─ core/
│  │  ├─ __init__.py
│  │  ├─ bot.py                   # Bot 构造与基础事件
│  │  ├─ loader.py                # 扩展/cog 自动加载
│  │  └─ lifecycle.py             # 启停流程（on_ready、shutdown）
│  ├─ db/
│  │  ├─ __init__.py
│  │  ├─ engine.py                # 连接管理
│  │  ├─ base.py                  # 通用 DB 操作
│  │  └─ repositories/
│  │     ├─ __init__.py
│  │     ├─ user_repo.py
│  │     ├─ farm_repo.py
│  │     ├─ shop_repo.py
│  │     └─ stock_repo.py
│  ├─ cogs/
│  │  ├─ __init__.py
│  │  ├─ core/
│  │  │  ├─ __init__.py
│  │  │  ├─ admin.py
│  │  │  └─ general.py
│  │  └─ gameplay/
│  │     ├─ __init__.py
│  │     ├─ cat.py
│  │     ├─ farm.py
│  │     ├─ monopoly.py
│  │     ├─ ranking.py
│  │     ├─ shop.py
│  │     ├─ stock_market.py
│  │     └─ title.py
│  ├─ features/
│  │  ├─ __init__.py
│  │  ├─ profile/
│  │  │  ├─ __init__.py
│  │  │  ├─ cog.py
│  │  │  ├─ service.py            # 业务规则（由 data.py 拆分升级）
│  │  │  ├─ repository.py         # 模块专属 DB 封装（由 database.py 迁移）
│  │  │  └─ ui/
│  │  │     ├─ __init__.py
│  │  │     ├─ views.py
│  │  │     └─ modals.py
│  │  ├─ cat/
│  │  │  ├─ __init__.py
│  │  │  ├─ service.py
│  │  │  ├─ repository.py
│  │  │  └─ ui/
│  │  │     ├─ __init__.py
│  │  │     └─ views.py
│  │  └─ ...
│  ├─ shared/
│  │  ├─ __init__.py
│  │  ├─ checks.py
│  │  ├─ helpers.py
│  │  ├─ constants.py
│  │  └─ data/
│  │     ├─ __init__.py
│  │     ├─ map_data.py
│  │     └─ ...
│  └─ ui/
│     ├─ __init__.py
│     ├─ components/
│     │  ├─ __init__.py
│     │  ├─ buttons.py
│     │  └─ embeds.py
│     └─ themes.py
├─ tests/
│  ├─ __init__.py
│  ├─ test_profile.py
│  └─ ...
├─ main.py                         # 仅保留极薄入口，调用 app.bootstrap.run()
├─ requirements.txt
└─ README.MD
```

---

## 3. 模块拆分原则

1. **按职责分层**
	- `cogs/`：Discord 命令与事件入口。
	- `features/`：业务规则、模块内聚逻辑。
	- `db/`：数据库连接与仓储访问。
	- `ui/`：可复用交互组件（View/Modal/Button/Embed）。
	- `shared/`：公共工具、校验、常量、静态数据。

2. **Cog 保持“薄”**
	- Cog 只做参数解析、权限检查、调用 service。
	- 业务逻辑放 `features/*/service.py`。

3. **DB 访问统一出口**
	- 不在 cog 里直接 SQL。
	- 由 `db/repositories/*` 或 `features/*/repository.py` 封装。

4. **UI 组件可复用**
	- 模块专属 UI 放 `features/<module>/ui/`。
	- 跨模块通用 UI 放 `app/ui/components/`。

---

## 4. 旧文件到新结构映射（第一版）

- `main.py` -> `app/bootstrap.py` + 保留薄 `main.py`
- `cogs/admin.py` -> `app/cogs/core/admin.py`
- `cogs/general.py` -> `app/cogs/core/general.py`
- `cogs/cat.py` -> `app/cogs/gameplay/cat.py`
- `cogs/farm.py` -> `app/cogs/gameplay/farm.py`
- `cogs/monopoly.py` -> `app/cogs/gameplay/monopoly.py`
- `cogs/ranking.py` -> `app/cogs/gameplay/ranking.py`
- `cogs/shop.py` -> `app/cogs/gameplay/shop.py`
- `cogs/stock_market.py` -> `app/cogs/gameplay/stock_market.py`
- `cogs/title.py` -> `app/cogs/gameplay/title.py`
- `cogs/core/database.py` + `utils/db.py` -> `app/db/engine.py` + `app/db/base.py`
- `cogs/modules/profile/ui.py` -> `app/features/profile/ui/views.py`
- `cogs/modules/profile/database.py` -> `app/features/profile/repository.py`
- `cogs/modules/profile/data.py` -> `app/features/profile/service.py`
- `utils/checks.py` -> `app/shared/checks.py`
- `utils/helpers.py` -> `app/shared/helpers.py`
- `utils/*_data.py` -> `app/shared/data/*_data.py`

---

## 5. 分阶段重构计划（建议按顺序）

### Phase 0：建立骨架（不改逻辑）
- 创建 `app/` 目录及子包，补齐 `__init__.py`。
- 先复制文件到新位置，不删旧文件。
- 让 `main.py` 优先从新路径导入；失败时可临时回退旧导入。

### Phase 1：启动与加载解耦
- 把 bot 初始化、cog 加载、配置读取从 `main.py` 拆到：
  - `app/core/bot.py`
  - `app/core/loader.py`
  - `app/config/settings.py`

### Phase 2：DB 合并与仓储化
- 合并 `cogs/core/database.py` 与 `utils/db.py` 的重复能力。
- 统一连接生命周期，暴露 repository 接口。
- 先改一个模块（建议 profile）验证模式，再批量迁移。

### Phase 3：模块化 features
- 将 `cogs/modules/profile` 迁移到 `app/features/profile`。
- 把模块里的 UI/Service/Repository 明确分层。
- 其他玩法模块（cat/farm/shop/title/stock）按同模板迁移。

### Phase 4：Cog 瘦身
- 各 Cog 仅保留命令入口、权限检查、响应组织。
- 复杂业务逻辑移动到 `features/*/service.py`。

### Phase 5：清理旧路径
- 确认新路径稳定后，删除旧目录：
  - `cogs/modules/`（旧）
  - `utils/` 中已迁移文件
  - 旧 DB 封装文件

---

## 6. 重构验收清单

- 启动成功，cog 全部正常加载。
- 主要命令（admin/general/cat/farm/shop/stock/title）可执行。
- profile 相关 UI（View/Modal）交互正常。
- 数据库读写行为与重构前一致。
- 日志无明显导入路径错误、循环依赖错误。

---

## 7. 下一步实施建议

建议按以下最小可行顺序推进：
1. 先完成 Phase 0 + Phase 1（只搬结构与启动逻辑）。
2. 以 profile 为样板完成 Phase 2 + Phase 3。
3. 样板稳定后批量迁移其余 gameplay 模块。

如果你希望，我下一步可以直接按这个 README 开始执行 **Phase 0（创建新目录骨架 + 迁移入口）**，并保持功能不变。

---

## 8. 当前实施进度（2026-04-17）

已完成：
- 新增 `app/` 骨架目录与主要子包（`config/core/db/cogs/features/shared/ui`）。
- 启动入口已拆分到 `app/bootstrap.py`，`main.py` 改为薄入口调用。
- 新增 `app/core/loader.py` 与 `app/core/lifecycle.py`，承接插件加载与事件处理。
- 已将 `admin`、`general` 迁移到 `app/cogs/core/`（真实实现已放在新路径，旧路径为 shim）。
- 已将 `cat/farm/monopoly/ranking/shop/stock_market/title` 迁移到 `app/cogs/gameplay/`（真实实现已放在新路径，旧路径为 shim）。
- 已将 `profile` 拆分路径接入到 `app/features/profile/`（`cog/service/repository/ui` 兼容导出）。
- 已建立 `app/shared/` 与 `app/db/` 的兼容导出层，可逐步把旧 import 切换到新命名空间。
- 已完成主流程 Cog 对 `utils.*` 的首轮切换，改为从 `app.shared.*` / `app.db.*` 导入。
- 加载器已处理“新旧同名 cog 去重加载”，避免重复注册命令。

下一步建议：
1. 将 `app/features/profile/*` 从“兼容导出”升级为“真实实现文件”。
2. 合并 `utils/db.py` 与 `cogs/core/database.py` 的底层实现到 `app/db/`，完成后下线旧 DB 入口。
3. 当 `app/db` 与 `app/shared` 底层稳定后，移除 `utils/` 兼容层并清理旧路径。
