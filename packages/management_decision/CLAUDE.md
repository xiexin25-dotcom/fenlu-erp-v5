# Lane 4 · 管理决策 · CLAUDE.md

> **You are working in `feat/management-decision` worktree.**
> This lane is **downstream of all others** — most of your work consumes
> events and data from Lanes 1/2/3. You will be building largely against
> mocks until week 8 when the upstream lanes' data starts flowing.

## Scope

| 工信部场景 | 约束 | 优先级 |
|-----------|------|--------|
| 财务管理 (GL/AP/AR/Tax) | ★ | P1 |
| 人力资源 (HR/Payroll) |  | P1 |
| 协同办公 (Approval flow) |  | P2 |
| 决策支持 (BI/KPI) |  | P0 |

## Boundaries

✅ Allowed: `packages/management_decision/**`, `packages/shared/contracts/management.py` (with lock)
❌ Forbidden: any other lane

## Database

- Schema: `mgmt`
- Migration prefix: `mgmt_`

## Cross-lane (you are mostly the **consumer**)

| Direction | Source | What you do |
|-----------|--------|-------------|
| `← plm` | Redis Stream `plm-events` (`SalesOrderConfirmedEvent`) | Create AR row |
| `← scm` | Redis Stream `scm-events` (`PurchaseOrderApprovedEvent`) | Create AP row |
| `← mfg` | Redis Stream `mfg-events` (OEE/QC/Energy/Hazard) | Roll up into KPIs |
| `→ all` | `/mgmt/approval` REST endpoint | Approval flow service for everyone |
| `→ all` | Casbin enforcer service | Permission checks |

## Casbin policy ownership

The actual `require_permission` enforcement lives here. The foundation
provides a placeholder that always allows authenticated users; **you must
replace it** with a real Casbin enforcer that loads policies from
`mgmt.casbin_rules`. The model file is at `infra/casbin/model.conf`.

## BI architecture

- Use a **lightweight star schema** in `mgmt.bi_*` tables — no separate OLAP DB
- Roll-ups computed by Celery beat tasks (hourly for OEE, daily for finance)
- Frontend dashboards consume `GET /mgmt/bi/kpi/{code}?period=...` returning
  `KPIDataPointDTO[]`
- The领导驾驶舱 (executive dashboard) is the visible deliverable for 决策支持 三级 — make it pretty
