# Lane 4 · Management Decision · TASKS.md

## Sprint 1 (Week 3) · Finance core

### TASK-MGMT-001 · GL accounts + journal entries
- `GLAccount`, `JournalEntry`, `JournalLine` models
- Double-entry constraint enforced at the model layer
- `POST /mgmt/finance/journal` requires balanced lines or 422

### TASK-MGMT-002 · AP / AR from contracts
- `APRecord`, `ARRecord` matching contracts
- For now, create them via direct API; the event-driven creation comes later

## Sprint 2 (Week 4) · HR

### TASK-MGMT-003 · Employee + payroll
- `Employee` model (linked to `User` from foundation via `user_id`)
- `Payroll` model with monthly periods
- `POST /mgmt/hr/payroll/run?period=2026-04` generates rows from employees + attendance

### TASK-MGMT-004 · Attendance (port from V4)
- `Attendance` model
- ETL from V4 attendance data

## Sprint 3 (Week 5) · Approval engine + Casbin

### TASK-MGMT-005 · Approval flow engine
- `ApprovalDefinition`, `ApprovalInstance`, `ApprovalStep` models
- `POST /mgmt/approval` accepts `business_type + business_id + payload`
- Configurable steps per business_type (start with: linear N-step, no parallel)
- Other lanes call this for any state transition that needs human approval

### TASK-MGMT-006 · Real Casbin enforcer
- Replace foundation's placeholder `require_permission` with a real enforcer
- Load policies from `mgmt.casbin_rules` on startup, hot-reload via Redis pub/sub
- Use the model at `infra/casbin/model.conf` (RBAC with domain/tenant)

## Sprint 4 (Week 6) · BI scaffolding

### TASK-MGMT-007 · KPI definition registry
- `KPIDefinition` model matching contract
- Seed with ~20 KPIs covering all 16 工信部 scenarios
- `GET /mgmt/bi/kpis` lists, `GET /mgmt/bi/kpi/{code}` gets one

### TASK-MGMT-008 · Event consumers
- Background worker subscribes to `plm-events`, `scm-events`, `mfg-events`
- For each event type, an `@on(EventType.X)` handler updates relevant BI tables
- Use Redis Streams consumer groups (one per event type) for backpressure

## Sprint 5 (Week 7-8) · Dashboards

### TASK-MGMT-009 · Aggregation roll-ups
- Celery beat tasks: hourly for OEE, daily for finance, real-time for safety
- Write into `mgmt.bi_kpi_data_points` table

### TASK-MGMT-010 · Executive dashboard endpoint
- `GET /mgmt/bi/dashboards/exec` returns a structured payload covering:
  - Today's revenue (from AR)
  - This week's production output + OEE
  - Open safety hazards
  - Energy unit consumption trend
  - Cash position
- The frontend renders it as the 决策支持 三级 demo

## Sprint 6 (Week 9-10) · Polish + reports

### TASK-MGMT-011 · Three financial statements
- Balance sheet, income statement, cash flow
- Generated as PDF via the foundation's pdf skill (or weasyprint)
