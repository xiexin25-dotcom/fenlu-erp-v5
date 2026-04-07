# Lane 2 · 生产执行 · CLAUDE.md

> **You are working in `feat/production` worktree.** This sub-config overrides
> the root CLAUDE.md where conflicts exist. Read this file before every session.

## ⚠️ This is the failure-prone heavy hitter

5 of the 6 scenarios in this lane are **约束性场景** (constraint scenarios) that
must reach 三级 (level 3) for the project to pass 工信部 acceptance. Failure
here means the whole project fails. Treat every PR with extra rigor.

## Scope

| 工信部场景 | 约束 | 优先级 |
|-----------|------|--------|
| 计划排程 (APS) |  | P1 |
| 生产管控 (MES) | ★ | P0 |
| 质量管理 (QMS / SPC) | ★ | P0 |
| 设备管理 (EAM / OEE) | ★ | P0 |
| 安全生产 (EHS) | ★ | P0 |
| 能耗管理 (Energy + 碳) | ★ | P0 |

## Boundaries (do not violate)

✅ **Allowed to modify**:
- `packages/production/**`
- `packages/shared/contracts/production.py` (with `[shared]` commit prefix + lock)
- `packages/shared/contracts/events.py` (only events whose `source_lane = "mfg"`)

❌ **Forbidden**:
- Any other lane's directory
- `packages/shared/auth/`, `packages/shared/db/`, `packages/shared/models/` (foundation territory)
- Direct SQLAlchemy imports from other lanes — use HTTP + contracts

## Database

- All tables go in the **`mfg`** PostgreSQL schema
- All tables MUST mixin `TenantMixin` + `TimestampMixin` + `AuditMixin` from `packages.shared.db`
- Migrations live in `infra/alembic/versions/` with filename prefix `mfg_`
- For energy time-series, use a TimescaleDB hypertable on `mfg.energy_readings`

## Cross-lane integration (HTTP only)

| Direction | Endpoint | Purpose |
|-----------|----------|---------|
| `mfg → plm` | `GET /plm/bom/{id}` | Pull BOM for APS |
| `mfg → plm` | `GET /plm/routing/{id}` | Pull routing for APS |
| `mfg → scm` | `POST /scm/issue` | Request material issue |
| `mfg → scm` | `GET /scm/inventory?product_id=...` | Check stock before scheduling |
| `mfg → mgmt` | Redis Stream `mfg-events` | Push OEE/QC/Energy/Hazard events |

All cross-lane DTOs come from `packages.shared.contracts.*`. **Never** define
your own version of `BOMDTO`, `WorkOrderDTO` etc. — those live in contracts.

## Algorithms that require unit tests (no exceptions)

- OEE calculation (`availability × performance × quality`)
- SPC control limits (UCL/LCL/CL based on subgroup means)
- APS scheduling (even the first-version FIFO heuristic)
- Energy unit-consumption rollup (kWh per produced unit)

## Acceptance evidence (what 三级 audit looks for)

For each P0 scenario, you must produce:

1. **Closed-loop data flow** — every business event leaves a record that can be
   queried. No "phantom" actions.
2. **Integration evidence** — at least one downstream lane consumes your data.
3. **Anomaly handling** — what happens when a worker scans a wrong barcode? a
   sensor sends garbage? a planned maintenance is skipped? Each must have an
   explicit code path with a test.

## When in doubt

Read `packages/shared/contracts/production.py` first — it tells you what shape
your data must take. Read `TASKS.md` next for the concrete first-sprint plan.
