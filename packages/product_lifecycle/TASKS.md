# Lane 1 · Product Lifecycle · TASKS.md

## Sprint 1 (Week 3) · PLM core

### TASK-PLM-001 · Product master + version
- `Product`, `ProductVersion` models in `plm` schema
- Match `ProductSummary` from contracts
- `POST/GET /plm/products`, `POST /plm/products/{id}/versions`
- New version copies prior version's BOM (start with deep copy, optimize later)

### TASK-PLM-002 · BOM tree + items
- `BOM`, `BOMItem` models, self-referential through `component_id`
- `GET /plm/bom/{id}` returns `BOMDTO` with full tree
- Cycle detection on insert (raise 422)
- Total cost rollup from component costs (recursive query is fine for v1)

### TASK-PLM-003 · CAD attachment to MinIO
- `POST /plm/products/{id}/cad` accepts multipart upload
- Streams to MinIO bucket `plm-cad` with key `tenant_id/product_id/version/filename`
- Stores key + size + checksum in `cad_attachments` table

## Sprint 2 (Week 4) · Routing + ECN

### TASK-PLM-004 · Routing & operations
- `Routing`, `RoutingOperation` models matching `RoutingDTO`
- `GET /plm/routing/{id}` (called by Lane 2 APS)

### TASK-PLM-005 · ECN (Engineering Change Notice) flow
- `ECN` model with state machine: draft → reviewing → approved → released → effective
- On `effective`, automatically version-bump the affected BOM/routing

## Sprint 3 (Week 5) · CRM

### TASK-PLM-006 · Customer 360 model
- `Customer` (migrate from old system) + `Contact`
- `GET /plm/customers/{id}/360` aggregates leads, opportunities, orders, tickets

### TASK-PLM-007 · Opportunity funnel
- `Lead`, `Opportunity` with stage transitions
- `GET /plm/crm/funnel?period=...` returns counts per stage for BI consumption

### TASK-PLM-008 · Quote → contract → order
- `Quote`, `SalesOrder` matching `SalesOrderDTO`
- On order confirm, emit `SalesOrderConfirmedEvent` to `plm-events`

## Sprint 4 (Week 6) · Aftersales

### TASK-PLM-009 · Service tickets with SLA
- `ServiceTicket` model matching contract
- SLA timer based on customer rating (A=4h, B=8h, C=24h)
- `POST /plm/service/tickets/{id}/close` requires NPS score (0-10)

## DoD: same as production lane.
