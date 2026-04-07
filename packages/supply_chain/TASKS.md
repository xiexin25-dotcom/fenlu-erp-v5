# Lane 3 · Supply Chain · TASKS.md

## Sprint 1 (Week 3) · ETL probe + supplier model

### TASK-SCM-001 · V4 ETL probe
- Read a real V4 dump (ask user for one)
- Map columns to V5 contract DTOs
- Write a Markdown file `migration/MAPPING.md` documenting every column

### TASK-SCM-002 · Supplier + rating
- `Supplier`, `SupplierRating` models matching `SupplierSummary`
- `POST/GET /scm/suppliers`
- Tier transitions (strategic/preferred/approved/blacklisted) require approval
  via Lane 4 `/mgmt/approval` endpoint

## Sprint 2 (Week 4) · Purchase

### TASK-SCM-003 · PR → RFQ → PO → receipt chain
- `PurchaseRequest`, `RFQ`, `PurchaseOrder`, `PurchaseReceipt` models
- Endpoints for each, with status transitions enforced
- On PO approval, emit `PurchaseOrderApprovedEvent` to `scm-events`

### TASK-SCM-004 · BOM-driven purchase
- `POST /scm/purchase-from-bom` (called by Lane 1) — explode BOM, group by
  supplier, create PRs
- Test with mocked Lane 1

## Sprint 3 (Week 5) · Warehouse

### TASK-SCM-005 · Multi-warehouse + locations
- `Warehouse`, `Location` (4-level hierarchy: warehouse → zone → aisle → bin)
- `POST/GET /scm/warehouses`, `/scm/locations`

### TASK-SCM-006 · Inventory + stock moves
- `Inventory`, `StockMove` models matching DTOs
- `GET /scm/inventory` with filters by product, warehouse, batch
- All inventory mutations go through `StockMove` (no direct UPDATE)
- `POST /scm/issue` (called by Lane 2) decrements inventory + writes a move

### TASK-SCM-007 · Stocktake (盘点) flow
- `Stocktake` header + `StocktakeLine`
- Variance handling: auto-create adjustment moves on confirm

### TASK-SCM-008 · Migrate V4 data
- Run the ETL from TASK-SCM-001 against full V4 dump
- Reconciliation report
- This task is the lane's main acceptance milestone
