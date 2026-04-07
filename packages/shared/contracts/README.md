# `packages/shared/contracts/` · 跨 Lane 契约包

> **这是 4 条 worktree 之间唯一允许的耦合点。**
> 改这里 = 改宪法,必须发起 RFC + @ 全部 lane owner + 合并到 `feat/foundation` 后再 rebase 到各 lane。

## 文件结构

```
packages/shared/contracts/
├── __init__.py              # 公共导出
├── base.py                  # BaseSchema / Money / Quantity / 分页 / 公共枚举
├── product_lifecycle.py     # Lane 1 对外 DTO (PLM/CRM/售后)
├── production.py            # Lane 2 对外 DTO (MES/QMS/EAM/EHS/能耗)
├── supply_chain.py          # Lane 3 对外 DTO (采购/仓储)
├── management.py            # Lane 4 对外 DTO (财务/HR/协同/BI/KPI)
└── events.py                # Redis Streams 异步事件
```

## 设计原则

| # | 原则 | 强制力 |
|---|------|--------|
| 1 | **只放 DTO,不放业务逻辑、不放 SQLAlchemy 模型** | 强制 |
| 2 | **所有 DTO 继承 `BaseSchema`**(`extra="forbid"` 防止偷塞字段) | 强制 |
| 3 | **跨 lane 一律走 REST 同步 + Redis Streams 异步**,禁止直接 import 对方模型 | 强制 |
| 4 | **金额一律用 `Money`,数量一律用 `Quantity`**,禁止裸 `float` / `Decimal` | 强制 |
| 5 | **枚举一律 `StrEnum`**(序列化/反序列化无歧义) | 强制 |
| 6 | **改本目录任何文件 → commit message 必须前缀 `[shared]`** | 强制 |
| 7 | **第 10 周后冻结**,只允许 bugfix,不允许加字段 | 强制 |

## 跨 Lane 调用矩阵

| 调用方 → 被调用方 | 同步接口 | 异步事件 |
|-------------------|----------|----------|
| Lane 2 → Lane 1   | `GET /plm/bom/{id}` 拉 BOM | — |
| Lane 2 → Lane 1   | `GET /plm/routing/{id}` 拉工艺 | — |
| Lane 2 → Lane 3   | `POST /scm/issue` 领料 | — |
| Lane 1 → Lane 3   | `POST /scm/purchase-from-bom` 反算采购 | — |
| Lane 3 → Lane 4   | — | `po.approved` → 自动挂应付 |
| Lane 1 → Lane 4   | — | `sales_order.confirmed` → 挂应收 |
| Lane 2 → Lane 4   | — | `oee.calculated` `qc.failed` `energy.*` `hazard.*` → BI 看板 |
| 任意 → Lane 4     | `POST /mgmt/approval` 发起审批 | `approval.requested` |

## 工信部 16 场景与契约对照

| 场景 | 约束 | 主要契约 DTO |
|------|------|--------------|
| 产品设计 ★ | ★ | `BOMDTO`, `ProductSummary` |
| 工艺设计 | | `RoutingDTO`, `RoutingOperationDTO` |
| 营销管理 ★ | ★ | `CustomerSummary`, `SalesOrderDTO` |
| 售后服务 | | `ServiceTicketSummary` |
| 计划排程 | | `WorkOrderDTO` (包含 planned_start/end) |
| 生产管控 ★ | ★ | `WorkOrderDTO`, `WorkOrderCompletedEvent` |
| 质量管理 ★ | ★ | `QCInspectionDTO`, `QCFailedEvent` |
| 设备管理 ★ | ★ | `EquipmentSummary`, `OEERecordDTO`, `EquipmentFaultEvent` |
| 安全生产 ★ | ★ | `SafetyHazardDTO`, `HazardReportedEvent` |
| 能耗管理 ★ | ★ | `EnergyReadingDTO`, `UnitConsumptionDTO`, `EnergyThresholdBreachedEvent` |
| 采购管理 ★ | ★ | `PurchaseOrderDTO`, `SupplierSummary`, `PurchaseOrderApprovedEvent` |
| 仓储物流 | | `InventoryDTO`, `StockMoveDTO` |
| 财务管理 ★ | ★ | `APRecordDTO`, `ARRecordDTO` |
| 人力资源 | | `EmployeeSummary` |
| 协同办公 | | `ApprovalRequest`, `ApprovalStepDTO` |
| 决策支持 | | `KPIDefinitionDTO`, `KPIDataPointDTO` |

✅ **16 场景全部有对应契约入口,可作为合规自查表。**

## 第 1 周该做什么

1. 把本目录原封不动放进 `feat/foundation` 分支,跑 `ruff check` + `mypy --strict`
2. 写一份 `tests/test_contracts.py`,对每个 DTO 做 round-trip 序列化测试
3. 在根 `CLAUDE.md` 加一条规则:**任何 lane 的 PR 如果包含 `from packages.<其他lane>` 的 import,CI 直接拒绝**
4. 4 条 lane 各自从 `feat/foundation` checkout 开干

## 后续要补的(本骨架未覆盖)

- [ ] `events.py` 里每个 `EventType` 都补完整 payload class(我只示例了 6 个)
- [ ] `base.py` 加 `AuditMixin`(操作人、操作 IP、操作来源)
- [ ] 加 OpenAPI 自动导出脚本,让前端 TS 端能 `openapi-typescript` 生成类型
- [ ] 加 `contracts/v1/` 版本目录,为将来灰度升级留接口
