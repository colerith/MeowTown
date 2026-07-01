# MeowTown 架构设计说明

本文档定义重构后的分层边界、依赖方向、模块模板与实施规则。
目标是保证后续继续拆分时：
- 不出现循环依赖
- 业务逻辑可测试
- 旧路径可平滑下线

---

## 1. 分层职责

### app/core
- 负责启动、生命周期、日志、扩展加载。
- 不承载玩法业务逻辑。

### app/cogs
- 负责 Discord 命令入口、参数解析、权限检查、响应组装。
- 通过调用 feature service 或 db 接口完成动作。
- 保持“薄层”。

### app/features
- 负责业务规则、模块内聚逻辑。
- 推荐每个 feature 拆分为：
  - cog.py（若该 feature 需要独立命令组）
  - service.py（纯业务规则）
  - repository.py（模块专属数据访问）
  - ui/（模块专属 View/Modal）

### app/db
- 负责数据库初始化、连接、通用数据访问函数。
- engine.py 管连接与建表迁移。
- repositories/ 放按领域拆分的仓储实现（逐步迁移目标）。

### app/shared
- 负责跨模块复用的常量、检查器、帮助方法、静态数据。
- shared/data 只存静态配置数据，不含 I/O 副作用。

### app/ui
- 负责跨 feature 通用 UI 组件。
- feature 专属 UI 不放这里，放 feature/ui。

---

## 2. 依赖方向（强约束）

允许依赖方向：
- core -> cogs, db, shared
- cogs -> features, db, shared, ui
- features -> db, shared, ui
- ui -> shared
- db -> shared（仅必要常量）

禁止依赖方向：
- db -> cogs
- db -> features
- shared -> cogs/features/db
- feature A 直接 import feature B 的 repository（通过 service 接口转发）

---

## 3. 代码边界规则

### Rule 1: Cog 不直接写 SQL
- SQL 只能放在 app/db 或 app/features/*/repository.py。

### Rule 2: Service 保持可测试
- service.py 尽量写成纯函数或轻副作用函数。
- 参数和返回值使用明确结构（后续可补 dataclass 或 TypedDict）。

### Rule 3: UI 不做业务决策
- ui 层只负责交互事件和展示。
- 业务判断委托给 service/repository。

### Rule 4: 旧路径只保留 shim
- 该阶段已完成，旧路径已删除。
- 不再往旧路径恢复任何业务逻辑。

---

## 4. Feature 模板

推荐结构：

```text
app/features/<feature>/
├─ __init__.py
├─ service.py
├─ repository.py
├─ cog.py                 # 可选
└─ ui/
   ├─ __init__.py
   ├─ views.py
   └─ modals.py
```

实施顺序：
1. 先把旧实现拷贝到新路径并跑通。
2. 再把旧文件改成 shim 回指新路径。
3. 最后重构 service/repository 内部代码质量。

---

## 5. DB 迁移策略

### 当前状态
- app/db 已承接真实实现。
- loader 已收敛为仅发现并加载 app/cogs 扩展。
- `user_repo.py`、`farm_repo.py`、`inventory_repo.py`、`title_repo.py` 已落地。
- `ranking_repo.py`、`monopoly_repo.py` 已开始承接跨表查询与玩法状态更新。
- `stock_repo.py` 已落地，`stock_market.py` 已从重复旧实现收敛回单份主实现。
- `cat/farm/title/shop/shared.checks` 已开始直接依赖 `app/db/repositories/*`。
- `monopoly.py` 的初始化迁移语句已并回 `engine.py`，主玩法流程与初始化职责已完成分离。
- `app.db.base` 与 `utils/*` 兼容层已移除。

### 下一步
1. 继续推进 gameplay feature 化，将更多纯业务逻辑从 cog 下沉到 `features/*/service.py`。
2. 为后续新拆出的 service / repository 持续补回归测试，避免出现半迁移状态。

---

## 6. shared/data 治理

当前部分 shared/data 仍是 import * 兼容导出。
设计目标：将其升级为真实数据文件，避免星号导入。

规则：
- 显式导出 __all__。
- 不在数据模块中执行数据库/网络 I/O。
- 仅保留常量与纯计算辅助函数。

---

## 7. 测试与验收基线

最低验收标准：
1. Bot 启动成功，扩展加载无异常。
2. 关键命令路径可执行：市民、农场、商店、大富翁、股市、称号、排行榜。
3. Profile UI 交互正常。
4. 数据库迁移与读写不回归。
5. 项目中不再出现新增的旧路径业务实现。

当前测试进度：
- 已落地 repository 集成测试：`user_repo`、`farm_repo`、`inventory_repo`、`title_repo`、`ranking_repo`、`stock_repo`、`monopoly_repo`。
- 已落地 feature / service 单元测试：`profile.service`、`monopoly.service`、`stock_market.service`。
- 已补 `app/features/profile/repository.py` 的回归测试，并修正其旧 `citizens` 表遗留为当前 `users` 表结构。

---

## 8. 收尾策略

按以下顺序收尾：
1. 完成 shared/data 实体化。
2. 清理 cogs/modules 下 shim。
3. 清理 cogs 下 shim（确认 loader 仅加载 app/cogs 后）。
4. 清理 utils 下 shim。
5. 更新 README 最终目录树与启动说明。

当前执行进度补充：
- 第 1-3 步已完成（shared/data 实体化完成，legacy cogs 已移除）。
- 第 4-5 步已完成（`utils/` shim 与 `app.db.base` 已删除，README 已同步更新）。
- 截至 2026-06-28，`stock_market.py` 与 `monopoly.py` 已完成主流程 repository 迁移；数据库迁移职责已统一回 `engine.py`。
- 截至 2026-07-01，测试已覆盖仓储主路径与首批 feature service，`.gitignore` 已补齐，`profile` feature repository 遗留旧表结构已完成收尾。
