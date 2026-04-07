# 分路链式工业互联网系统 V5.0

> 工信部《2024 版中小企业数字化水平评测指标(16 项场景)》三级集成级目标实现。

## 快速开始

```bash
# 1. 装依赖
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync

# 2. 起依赖服务
cp .env.example .env
docker compose up -d postgres redis minio

# 3. 初始化 schemas
psql postgresql://fenlu:fenlu_dev@localhost:5432/fenlu_v5 -f infra/init.sql

# 4. 跑迁移
uv run alembic -c infra/alembic.ini upgrade head

# 5. 启动 API
uv run uvicorn apps.api_gateway.main:app --reload --port 8000

# 6. 验证
curl http://localhost:8000/health
# {"status":"ok"}

# 7. OpenAPI 文档
open http://localhost:8000/docs
```

## 项目结构

```
fenlu-v5/
├── CLAUDE.md                    # 项目宪法
├── pyproject.toml               # uv workspace
├── docker-compose.yml
├── infra/
│   ├── init.sql                 # 4 lane schemas
│   ├── alembic.ini
│   └── alembic/
│       ├── env.py
│       └── versions/
│           └── 0001_foundation.py
├── packages/
│   └── shared/                  # 跨 lane 共享 (foundation 提供)
│       ├── db/                  # async engine, base, mixins
│       ├── auth/                # JWT, password, FastAPI deps
│       ├── models/              # Tenant, User, Role, Organization
│       └── contracts/           # 跨 lane Pydantic schema
├── apps/
│   └── api_gateway/             # FastAPI 主入口
│       ├── main.py
│       ├── settings.py
│       └── routers/
│           ├── health.py
│           ├── auth.py          # /auth/login, /refresh, /me
│           └── orgs.py          # /orgs CRUD
└── .github/workflows/ci.yml     # ruff + mypy + pytest + 跨 lane import 检查
```

## 后续 4 lane 开发

读 `CLAUDE.md` 的 worktree 表,然后:

```bash
git worktree add ../fenlu-v5-product       -b feat/product-lifecycle    main
git worktree add ../fenlu-v5-production    -b feat/production           main
git worktree add ../fenlu-v5-supply-chain  -b feat/supply-chain         main
git worktree add ../fenlu-v5-management    -b feat/management-decision  main
```
