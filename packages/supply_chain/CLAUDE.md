# Lane 3 · 供应链 · CLAUDE.md

> **You are working in `feat/supply-chain` worktree.**
> This is the **most stable** lane — most functionality migrates from V4
> rather than being built fresh. Bias towards conservative changes.

## Scope

| 工信部场景 | 约束 | 优先级 |
|-----------|------|--------|
| 采购管理 | ★ | P2 (mostly migration) |
| 仓储物流 |  | P2 (mostly migration) |

## Boundaries

✅ Allowed: `packages/supply_chain/**`, `packages/shared/contracts/supply_chain.py` (with lock)
❌ Forbidden: any other lane

## Database

- Schema: `scm`
- Migration prefix: `scm_`

## Cross-lane

| Direction | Endpoint | Purpose |
|-----------|----------|---------|
| `scm` serves | `POST /scm/purchase-from-bom` | Lane 1 BOM-driven purchase |
| `scm` serves | `POST /scm/issue` | Lane 2 material issue |
| `scm` serves | `GET /scm/inventory` | Lane 1/2 stock query |
| `scm → mgmt` | Redis Stream `scm-events` | PO approved → AP |

## Migration approach (V4 → V5)

The old system has solid 采购/仓储 modules. Don't rewrite — port. Steps:

1. Map V4 tables to V5 contracts (`PurchaseOrderDTO`, `InventoryDTO`, ...)
2. Write ETL scripts in `packages/supply_chain/migration/` that read V4 dumps
   and produce V5-shaped CSV
3. Loader inserts into `scm.*` tables
4. Reconciliation: row count + sum-of-amounts assertion per tenant per table
5. Run a dry-run on a real V4 dump in week 4 to catch surprises early
