# 分路链式工业互联网系统 V5.0 · CLAUDE.md

> 这是项目宪法。任何 Claude Code 实例进入本仓库前必须先读完。

## 目标
工信部《2024 版中小企业数字化水平评测指标(16 项场景)》**三级集成级**,9 个约束性场景必达三级。

## 技术栈
- **后端:** FastAPI 0.115+ / SQLAlchemy 2.0 异步 / asyncpg / Pydantic v2 / Alembic
- **前端:** React 18 + TypeScript + Vite + TanStack Query + Zustand + shadcn/ui
- **数据:** PostgreSQL 16 (TimescaleDB 扩展用于能耗) + Redis 7 + MinIO
- **包管理:** uv (Python) + pnpm (Node)

## Worktree 边界 (绝对不能越界)

本仓库使用 4+1 worktree 并行开发,**你正在工作的 worktree 由 git 当前分支决定**:

| 分支 | 允许修改的目录 | 端口 | DB schema |
|------|----------------|------|-----------|
| `main` / `feat/foundation` | 全仓 (基础设施) | 8000 | public |
| `feat/product-lifecycle` | `packages/product_lifecycle/` + `packages/shared/` (须挂锁) | 8001 | plm |
| `feat/production` | `packages/production/` + `packages/shared/` (须挂锁) | 8002 | mfg |
| `feat/supply-chain` | `packages/supply_chain/` + `packages/shared/` (须挂锁) | 8003 | scm |
| `feat/management-decision` | `packages/management_decision/` + `packages/shared/` (须挂锁) | 8004 | mgmt |

**🚫 跨 lane 通信硬规则:**
1. **绝不**直接 `from packages.<其他lane> import ...` SQLAlchemy 模型 — CI 会拒绝
2. 同步调用走 REST + `packages/shared/contracts/` 下的 Pydantic schema
3. 异步事件走 Redis Streams,事件类型必须在 `packages/shared/contracts/events.py` 声明
4. 改 `packages/shared/` 任何文件 → commit message 必须前缀 `[shared]` 并 @ 全部 lane owner

## 代码规范
- Python: ruff + mypy strict, 函数 ≤ 50 行,所有公共函数必须有类型注解
- TS: eslint + prettier, 组件 ≤ 200 行
- 测试: pytest 后端覆盖率 ≥ 70%, 关键算法必须有单测
- 提交: Conventional Commits, scope 必填 (`plm`/`mfg`/`scm`/`mgmt`/`shared`/`infra`)

## 数据库约定
- 每个 lane 用独立 schema (`plm`/`mfg`/`scm`/`mgmt`),`shared` 用 `public`
- 所有业务表必须 mixin `TenantMixin` (多租户隔离)
- 所有业务表必须 mixin `TimestampMixin` + `AuditMixin`
- 迁移文件统一放 `infra/alembic/versions/`,文件名前缀标 lane (如 `mfg_0003_add_oee.py`)

## 命令速查

```bash
# 安装
uv sync

# 启动依赖 (postgres + redis + minio)
docker compose up -d postgres redis minio

# 初始化 schema (首次)
psql -h localhost -U fenlu -d fenlu_v5 -f infra/init.sql

# 迁移
uv run alembic -c infra/alembic.ini upgrade head

# 启动 API (foundation, port 8000)
uv run uvicorn apps.api_gateway.main:app --reload --port 8000

# 各 lane 启动自己的 API
# Lane 1: --port 8001, Lane 2: 8002, Lane 3: 8003, Lane 4: 8004

# 跑测试
uv run pytest

# Lint + 类型检查
uv run ruff check .
uv run mypy packages apps
```

## 当前进度
- [x] foundation: auth/RBAC/org/db/CI/Docker/tests
- [x] shared/contracts: 跨 lane 契约 schema (产品/生产/供应链/管理 + events)
- [x] 4 个 lane 目录骨架 (含 sub-CLAUDE.md + TASKS.md)
- [ ] Lane 1 product-lifecycle (任务卡见 packages/product_lifecycle/TASKS.md)
- [ ] Lane 2 production - 失分重灾区,优先建 (任务卡见 packages/production/TASKS.md)
- [ ] Lane 3 supply-chain (任务卡见 packages/supply_chain/TASKS.md)
- [ ] Lane 4 management-decision (任务卡见 packages/management_decision/TASKS.md)

## Lane 任务卡入口

进入任何 worktree 后,先读两个文件:
1. `packages/<lane>/CLAUDE.md` — 该 lane 的边界与硬规则
2. `packages/<lane>/TASKS.md` — 第一冲刺的任务卡清单

## 工信部 16 场景对照
见 `packages/shared/contracts/README.md`。
