# Lane 1 · 产品生命周期 · CLAUDE.md

> **You are working in `feat/product-lifecycle` worktree.**

## Scope

| 工信部场景 | 约束 | 优先级 |
|-----------|------|--------|
| 产品设计 (PLM) | ★ | P0 |
| 工艺设计 (Routing) |  | P1 |
| 营销管理 (CRM) | ★ | P0 |
| 售后服务 |  | P1 |

## Boundaries

✅ Allowed: `packages/product_lifecycle/**`, `packages/shared/contracts/product_lifecycle.py` (with lock)
❌ Forbidden: any other lane's directory; direct SQLAlchemy import from other lanes

## Database

- Schema: `plm`
- All tables mixin `TenantMixin + TimestampMixin + AuditMixin`
- Migration filename prefix: `plm_`
- CAD attachments stored in MinIO bucket `plm-cad`, table only stores object key

## Cross-lane integration

| Direction | Endpoint | Purpose |
|-----------|----------|---------|
| `plm → scm` | `POST /scm/purchase-from-bom` | Trigger purchase from BOM |
| `mfg → plm` | `GET /plm/bom/{id}` (you serve this) | MES pulls BOM |
| `mfg → plm` | `GET /plm/routing/{id}` (you serve this) | MES pulls routing |
| `plm → mgmt` | Redis Stream `plm-events` | Push sales orders, service NPS |

## Hard rules

- BOM versions are **immutable**. A change creates a new version + an ECN record.
- Customer 360 view must aggregate from leads + opportunities + orders + tickets in
  ≤ 3 queries — do not n+1.
- Quotes/orders carry money — always use `Money` from `packages.shared.contracts.base`,
  never raw `Decimal`.

## Acceptance evidence

- 产品设计 三级: BOM ↔ CAD linkage, version history, ECN approval flow
- 营销管理 三级: lead → opportunity → quote → contract → order full chain queryable
