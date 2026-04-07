# Lane 2 · Production · TASKS.md

> First-sprint task cards for Claude Code. Work through them in order.
> Each task is sized for one focused session (1-3 hours of Claude Code time).

## Sprint 1 (Week 3-4) · 生产管控 base

### TASK-MFG-001 · WorkOrder model + migration
**Goal**: create the central work order table that everything else hangs off.

**Acceptance**:
- `packages/production/models/work_order.py` with `WorkOrder` SQLAlchemy model
- All fields match `packages.shared.contracts.production.WorkOrderDTO`
- Mixin `TenantMixin + TimestampMixin + AuditMixin`
- Schema = `mfg`
- Alembic migration `mfg_0001_work_order.py`
- One pytest in `packages/production/tests/test_work_order.py` that creates a row

**Out of scope**: APIs, services. Just the model.

---

### TASK-MFG-002 · WorkOrder CRUD endpoints
**Goal**: REST endpoints to create, read, list, transition status of work orders.

**Acceptance**:
- `packages/production/api/work_orders.py` with `POST/GET/PATCH /mfg/work-orders`
- All responses use `WorkOrderDTO` from contracts
- Status transitions enforced (planned → released → in_progress → completed → closed; can't skip)
- 401 if no token, 403 if wrong tenant
- pytest covers happy path + 1 forbidden transition

---

### TASK-MFG-003 · Pull BOM from Lane 1 (HTTP integration)
**Goal**: when releasing a work order, fetch the BOM from Lane 1 to validate it exists.

**Acceptance**:
- A `BomClient` in `packages/production/services/bom_client.py` that calls
  `GET http://localhost:8001/plm/bom/{id}` and parses into `BOMDTO`
- Work order release endpoint uses it and returns 422 if BOM not found
- Use `httpx.AsyncClient` with timeout
- Mock the HTTP call in pytest using `respx` or `httpx.MockTransport`

---

### TASK-MFG-004 · Job ticket + report-back (报工)
**Goal**: shop-floor workers scan a job ticket and report quantity completed/scrapped.

**Acceptance**:
- `JobTicket` model linked to `WorkOrder`
- `POST /mfg/job-tickets/{id}/report` accepts `{completed_qty, scrap_qty, minutes}`
- Updates `work_order.completed_quantity` atomically
- Emits `WorkOrderCompletedEvent` to Redis Stream `mfg-events` when work order hits its planned qty

## Sprint 2 (Week 5) · QMS

### TASK-MFG-005 · QC inspection model + endpoints
- `QCInspection` model matching `QCInspectionDTO` from contracts
- `POST /mfg/qc/inspections`, `GET /mfg/qc/inspections?work_order_id=...`
- Auto-emit `QCFailedEvent` when result = FAIL

### TASK-MFG-006 · SPC control chart endpoint
- `GET /mfg/qc/spc?product_id=...&period=30d`
- Compute UCL / LCL / CL from inspection records
- Return data ready for frontend Recharts (don't render here)
- **Must have unit test** for the SPC math (use known textbook examples)

## Sprint 3 (Week 6) · EAM

### TASK-MFG-007 · Equipment + maintenance plan models
- `Equipment`, `MaintenancePlan`, `MaintenanceLog`, `FaultRecord`
- Schedule cron job (Celery) to generate maintenance work orders from plans

### TASK-MFG-008 · OEE calculation service
- `OEEService.calculate(equipment_id, date)` → `OEERecordDTO`
- Pull data from job tickets + fault records + QC results
- **Unit test required** with known inputs → known OEE

## Sprint 4 (Week 6) · EHS + Energy

### TASK-MFG-009 · Hazard reporting closed loop
- `SafetyHazard` model with state machine: reported → assigned → rectifying → verified → closed
- `POST /mfg/safety/hazards`, `PATCH /mfg/safety/hazards/{id}/transition`
- Each transition writes an audit log row

### TASK-MFG-010 · Energy meter + reading ingestion
- `EnergyMeter`, `EnergyReading` (TimescaleDB hypertable)
- `POST /mfg/energy/readings` accepts batch of readings (Modbus gateway will call this)
- `GET /mfg/energy/unit-consumption?product_id=...&period=...` rolls up
- For now, fake the meter — the real Modbus integration is out of Sprint 4 scope

## Sprint 5 (Week 7) · APS

### TASK-MFG-011 · Simple APS (FIFO + capacity)
- `POST /mfg/aps/run` takes a date range, returns proposed schedule
- v1 algorithm: FIFO by promised_delivery, respect workstation capacity
- Output: list of `(work_order_id, workstation_id, planned_start, planned_end)`
- **Do NOT** introduce OR-Tools or other heavy solvers in v1

---

## Definition of Done (every task)

- [ ] Code passes `make lint` (ruff + mypy strict)
- [ ] Tests pass `make test`
- [ ] Test coverage for new code ≥ 70%
- [ ] Migration applies cleanly with `make migrate`
- [ ] Conventional commit with `feat(mfg):` prefix
- [ ] Updated this TASKS.md to mark task as done
