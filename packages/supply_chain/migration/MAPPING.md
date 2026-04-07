# V4 → V5 供应链数据迁移映射

> **TASK-SCM-001** · ETL probe
>
> V4 dump 尚未提供,本文档基于 V4 典型 ERP 采购/仓储模块的表结构模拟推导。
> 拿到真实 dump 后需逐表核对并更新本文件。

---

## 约定

| 符号 | 含义 |
|------|------|
| `=`  | 直接映射,类型兼容 |
| `~`  | 需要转换 (类型/格式/编码) |
| `+`  | V5 新增字段,需给默认值或从其他表关联 |
| `-`  | V4 有但 V5 不保留,仅归档 |
| `?`  | 待确认,需看真实 dump |

---

## 1. 供应商 · `t_supplier` → `scm.supplier`

### V5 目标 DTO: `SupplierSummary`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | `id` | UUID | ~ | 生成 UUID,保留 `legacy_id` 做反查 |
| `supplier_code` | VARCHAR(32) | `code` | str | = | 直接迁移 |
| `supplier_name` | VARCHAR(128) | `name` | str | = | 直接迁移 |
| `contact_person` | VARCHAR(64) | — | — | - | 迁入 `supplier_contacts` 子表或 JSON 字段 |
| `phone` | VARCHAR(32) | — | — | - | 同上 |
| `address` | VARCHAR(256) | — | — | - | 同上 |
| `bank_account` | VARCHAR(64) | — | — | - | 迁入财务子表 (Lane 4) |
| `tax_no` | VARCHAR(32) | — | — | - | 迁入财务子表 (Lane 4) |
| `level` | TINYINT (1-4) | `tier` | SupplierTier | ~ | 1→strategic, 2→preferred, 3→approved, 4→blacklisted |
| `score` | DECIMAL(5,2) | `rating_score` | float [0,100] | ~ | 若 V4 用百分制直接映射; 若五分制则 ×20 |
| `is_active` | TINYINT(1) | `is_online` | bool | ~ | 1→true, 0→false |
| `create_time` | DATETIME | `created_at` | datetime (UTC) | ~ | V4 通常为 Asia/Shanghai,需转 UTC |
| `update_time` | DATETIME | `updated_at` | datetime (UTC) | ~ | 同上 |
| — | — | `tenant_id` | UUID | + | 按 V4 的 `company_id` 或统一赋值 |

### 注意事项
- V4 可能有 `supplier_type` (原材料/设备/服务),V5 暂无对应字段,建议存 metadata 或后续扩展
- V4 `bank_account` / `tax_no` 属于 Lane 4 (mgmt) 财务域,ETL 时需拆分给 Lane 4

---

## 2. 供应商评分 · `t_supplier_score` → `scm.supplier_rating`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `supplier_id` | INT | `supplier_id` | UUID | ~ | 通过 legacy_id 查找 |
| `year` | SMALLINT | `period_start` / `period_end` | date | ~ | year→当年1月1日~12月31日 |
| `month` | TINYINT | (同上) | — | ~ | 合并 year+month 为 period |
| `quality_score` | DECIMAL(5,2) | `quality_score` | float | = | 直接迁移 |
| `delivery_score` | DECIMAL(5,2) | `delivery_score` | float | = | 直接迁移 |
| `price_score` | DECIMAL(5,2) | `price_score` | float | = | 直接迁移 |
| `service_score` | DECIMAL(5,2) | `service_score` | float | = | 直接迁移 |
| `total_score` | DECIMAL(5,2) | `rating_score` | float | = | 加权总分,直接迁移 |
| `create_time` | DATETIME | `created_at` | datetime | ~ | 时区转换 |

---

## 3. 采购申请 · `t_purchase_request` → `scm.purchase_request`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `request_no` | VARCHAR(32) | `request_no` | str | = | 直接迁移 |
| `department_id` | INT | `department_id` | UUID | ~ | 通过 legacy_id 查找 |
| `requester_id` | INT | `requested_by` | UUID | ~ | 用户表 legacy_id |
| `status` | VARCHAR/TINYINT | `status` | DocumentStatus | ~ | 见下方状态映射表 |
| `remark` | TEXT | `remark` | str | = | 直接迁移 |
| `create_time` | DATETIME | `created_at` | datetime | ~ | 时区转换 |
| `update_time` | DATETIME | `updated_at` | datetime | ~ | 时区转换 |
| `audit_user` | INT | `approved_by` | UUID | ~ | 用户表 legacy_id |
| `audit_time` | DATETIME | `approved_at` | datetime | ~ | 时区转换 |
| — | — | `tenant_id` | UUID | + | 默认赋值 |

### `t_purchase_request_detail` → `scm.purchase_request_line`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `request_id` | INT | `request_id` | UUID | ~ | 通过 legacy_id 查找 |
| `material_id` | INT | `product_id` | UUID | ~ | 产品表 legacy_id (来自 Lane 1) |
| `quantity` | DECIMAL(18,4) | `quantity.value` | Decimal | ~ | 拆为 Quantity(value, uom) |
| `unit` | VARCHAR(16) | `quantity.uom` | UnitOfMeasure | ~ | 中文单位→枚举: "件"→pcs, "千克"→kg 等 |
| `required_date` | DATE | `needed_by` | datetime | ~ | DATE→datetime |
| `remark` | VARCHAR(256) | `remark` | str | = | 直接迁移 |

---

## 4. 采购订单 · `t_purchase_order` → `scm.purchase_order`

### V5 目标 DTO: `PurchaseOrderDTO`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `order_no` | VARCHAR(32) | `order_no` | str | = | 直接迁移 |
| `supplier_id` | INT | `supplier_id` | UUID | ~ | 供应商 legacy_id 查找 |
| `status` | TINYINT/VARCHAR | `status` | DocumentStatus | ~ | 见状态映射表 |
| `total_amount` | DECIMAL(18,2) | `total_amount.amount` | Decimal(18,4) | ~ | 精度扩展 2→4 位小数 |
| `currency` | VARCHAR(8) | `total_amount.currency` | Currency | ~ | 默认 "CNY"; "美元"/"USD"→USD |
| `expected_date` | DATE | `expected_arrival` | datetime \| None | ~ | DATE→datetime |
| `buyer_id` | INT | `buyer_id` | UUID | ~ | 用户表 legacy_id |
| `contract_no` | VARCHAR(32) | `contract_no` | str \| None | = | 直接迁移 |
| `payment_terms` | VARCHAR(64) | `payment_terms` | str | = | 直接迁移 |
| `create_time` | DATETIME | `created_at` | datetime | ~ | 时区转换 |
| `update_time` | DATETIME | `updated_at` | datetime | ~ | 时区转换 |
| `audit_user` | INT | `approved_by` | UUID | ~ | 用户表 legacy_id |
| `audit_time` | DATETIME | `approved_at` | datetime | ~ | 时区转换 |
| — | — | `tenant_id` | UUID | + | 默认赋值 |

### `t_purchase_order_detail` → `scm.purchase_order_line`

### V5 目标 DTO: `PurchaseOrderLineDTO`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `order_id` | INT | `order_id` | UUID | ~ | PO legacy_id 查找 |
| `material_id` | INT | `product_id` | UUID | ~ | 产品表 legacy_id |
| `quantity` | DECIMAL(18,4) | `quantity.value` | Decimal | ~ | 拆为 Quantity |
| `unit` | VARCHAR(16) | `quantity.uom` | UnitOfMeasure | ~ | 中文单位→枚举 |
| `unit_price` | DECIMAL(18,4) | `unit_price.amount` | Decimal | = | 直接映射; currency 取表头 |
| `amount` | DECIMAL(18,2) | `line_total.amount` | Decimal(18,4) | ~ | 精度扩展 |
| `received_qty` | DECIMAL(18,4) | `received_quantity.value` | Decimal | = | 直接映射 |
| `tax_rate` | DECIMAL(5,2) | — | — | - | 税相关迁入 Lane 4 |
| `tax_amount` | DECIMAL(18,2) | — | — | - | 同上 |
| `remark` | VARCHAR(256) | `remark` | str | = | 直接迁移 |

---

## 5. 收货单 · `t_purchase_receipt` → `scm.purchase_receipt`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `receipt_no` | VARCHAR(32) | `receipt_no` | str | = | 直接迁移 |
| `order_id` | INT | `purchase_order_id` | UUID | ~ | PO legacy_id |
| `supplier_id` | INT | `supplier_id` | UUID | ~ | 供应商 legacy_id |
| `warehouse_id` | INT | `warehouse_id` | UUID | ~ | 仓库 legacy_id |
| `status` | TINYINT | `status` | DocumentStatus | ~ | 状态映射 |
| `receive_date` | DATE | `received_at` | datetime | ~ | DATE→datetime |
| `receiver_id` | INT | `received_by` | UUID | ~ | 用户表 legacy_id |
| `create_time` | DATETIME | `created_at` | datetime | ~ | 时区转换 |
| — | — | `tenant_id` | UUID | + | 默认赋值 |

### `t_purchase_receipt_detail` → `scm.purchase_receipt_line`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `receipt_id` | INT | `receipt_id` | UUID | ~ | 收货单 legacy_id |
| `material_id` | INT | `product_id` | UUID | ~ | 产品表 legacy_id |
| `order_qty` | DECIMAL | `ordered_quantity` | Quantity | ~ | 拆为 Quantity |
| `received_qty` | DECIMAL | `received_quantity` | Quantity | ~ | 拆为 Quantity |
| `rejected_qty` | DECIMAL | `rejected_quantity` | Quantity | ~ | 拆为 Quantity |
| `batch_no` | VARCHAR(32) | `batch_no` | str | = | 直接迁移 |
| `location_id` | INT | `location_id` | UUID | ~ | 库位 legacy_id |

---

## 6. 仓库 · `t_warehouse` → `scm.warehouse`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `warehouse_code` | VARCHAR(16) | `code` | str | = | 直接迁移 |
| `warehouse_name` | VARCHAR(64) | `name` | str | = | 直接迁移 |
| `address` | VARCHAR(256) | `address` | str | = | 直接迁移 |
| `manager_id` | INT | `manager_id` | UUID | ~ | 用户表 legacy_id |
| `is_active` | TINYINT(1) | `is_active` | bool | ~ | 1→true |
| `create_time` | DATETIME | `created_at` | datetime | ~ | 时区转换 |
| — | — | `tenant_id` | UUID | + | 默认赋值 |

### `t_warehouse_location` → `scm.location` (4 级层次)

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `warehouse_id` | INT | `warehouse_id` | UUID | ~ | 仓库 legacy_id |
| `location_code` | VARCHAR(32) | `code` | str | = | 直接迁移 |
| `location_name` | VARCHAR(64) | `name` | str | = | 直接迁移 |
| `parent_id` | INT | `parent_id` | UUID \| None | ~ | 自引用 legacy_id |
| `level` | TINYINT | `level` | LocationLevel | ~ | V4 可能只有 2 级,V5 为 4 级 (warehouse→zone→aisle→bin) |
| `is_active` | TINYINT(1) | `is_active` | bool | ~ | 1→true |

**注意:** V4 仓库库位可能只有 1-2 级层次,V5 要求 4 级。迁移时中间层级需按规则补全或置空。

---

## 7. 库存 · `t_inventory` → `scm.inventory`

### V5 目标 DTO: `InventoryDTO`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `material_id` | INT | `product_id` | UUID | ~ | 产品表 legacy_id |
| `warehouse_id` | INT | `warehouse_id` | UUID | ~ | 仓库 legacy_id |
| `location_id` | INT | `location_code` | str \| None | ~ | 通过 legacy_id 查库位 code |
| `quantity` | DECIMAL(18,4) | `on_hand.value` | Decimal | = | V4 现有量 = V5 on_hand |
| `available_qty` | DECIMAL(18,4) | `available.value` | Decimal | = | 直接映射 |
| `locked_qty` | DECIMAL(18,4) | `reserved.value` | Decimal | ~ | V4 locked ≈ V5 reserved |
| `in_transit_qty` | DECIMAL(18,4) | `in_transit.value` | Decimal | = | 直接映射 (V4 可能无此字段则默认 0) |
| `unit` | VARCHAR(16) | (各 Quantity 的 uom) | UnitOfMeasure | ~ | 中文单位→枚举 |
| `batch_no` | VARCHAR(32) | `batch_no` | str \| None | = | 直接迁移 |
| `expiry_date` | DATE | `expiry_date` | datetime \| None | ~ | DATE→datetime |
| `safety_stock` | DECIMAL(18,4) | `safety_stock` | Quantity | = | 直接映射 |
| `update_time` | DATETIME | `updated_at` | datetime | ~ | 时区转换 |
| — | — | `tenant_id` | UUID | + | 默认赋值 |

---

## 8. 出入库流水 · `t_stock_in` / `t_stock_out` → `scm.stock_move`

### V5 目标 DTO: `StockMoveDTO`

V4 通常将入库和出库分为两张表,V5 合并为 `stock_move` 并用 `type` 区分。

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `bill_no` | VARCHAR(32) | `move_no` | str | = | 直接迁移 |
| — (来自表名) | — | `type` | StockMoveType | ~ | 见下方类型映射 |
| `material_id` | INT | `product_id` | UUID | ~ | 产品表 legacy_id |
| `quantity` | DECIMAL(18,4) | `quantity.value` | Decimal | = | 直接映射 |
| `unit` | VARCHAR(16) | `quantity.uom` | UnitOfMeasure | ~ | 中文单位→枚举 |
| `warehouse_id` | INT | `from_location` / `to_location` | str | ~ | 入库: to_location=仓库code; 出库: from_location=仓库code |
| `location_id` | INT | (同上,更精确) | str | ~ | 库位 code |
| `ref_type` | VARCHAR(16) | — | — | ~ | 用于推导 StockMoveType |
| `ref_id` | INT | `reference_id` | UUID | ~ | 关联单据 legacy_id |
| `operator_id` | INT | `actor_id` | UUID | ~ | 用户表 legacy_id |
| `operate_time` | DATETIME | `created_at` | datetime | ~ | 时区转换 |
| `remark` | VARCHAR(256) | `remark` | str | = | 直接迁移 |
| — | — | `tenant_id` | UUID | + | 默认赋值 |

### StockMoveType 映射

| V4 来源 | V4 `ref_type` / 表 | V5 `type` |
|---------|-------------------|-----------|
| `t_stock_in` | ref_type="purchase" | `purchase_receipt` |
| `t_stock_in` | ref_type="produce" | `production_receipt` |
| `t_stock_in` | ref_type="transfer" | `transfer` |
| `t_stock_out` | ref_type="sale" | `sales_issue` |
| `t_stock_out` | ref_type="produce" | `production_issue` |
| `t_stock_out` | ref_type="transfer" | `transfer` |
| `t_stock_in`/`out` | ref_type="adjust" | `adjustment` |
| `t_stock_out` | ref_type="scrap" | `scrap` |

---

## 9. 盘点 · `t_stocktake` → `scm.stocktake`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `stocktake_no` | VARCHAR(32) | `stocktake_no` | str | = | 直接迁移 |
| `warehouse_id` | INT | `warehouse_id` | UUID | ~ | 仓库 legacy_id |
| `status` | TINYINT | `status` | DocumentStatus | ~ | 状态映射 |
| `stocktake_date` | DATE | `stocktake_date` | datetime | ~ | DATE→datetime |
| `operator_id` | INT | `created_by` | UUID | ~ | 用户表 legacy_id |
| `create_time` | DATETIME | `created_at` | datetime | ~ | 时区转换 |
| — | — | `tenant_id` | UUID | + | 默认赋值 |

### `t_stocktake_detail` → `scm.stocktake_line`

| V4 列 (推测) | V4 类型 | V5 列 | V5 类型 | 映射 | 转换规则 |
|---|---|---|---|---|---|
| `id` | INT | `id` | UUID | ~ | 生成 UUID |
| `stocktake_id` | INT | `stocktake_id` | UUID | ~ | 盘点单 legacy_id |
| `material_id` | INT | `product_id` | UUID | ~ | 产品表 legacy_id |
| `system_qty` | DECIMAL | `system_quantity` | Quantity | ~ | 拆为 Quantity |
| `actual_qty` | DECIMAL | `actual_quantity` | Quantity | ~ | 拆为 Quantity |
| `variance_qty` | DECIMAL | `variance` | Quantity | ~ | 拆为 Quantity (= actual - system) |
| `remark` | VARCHAR(256) | `remark` | str | = | 直接迁移 |

---

## 公共转换规则

### A. 主键 INT → UUID

所有 V4 `INT AUTO_INCREMENT` 主键迁移为 V5 `UUID`。ETL 需维护一张 `legacy_id_map` 表:

```
legacy_id_map (
    table_name  VARCHAR(64),
    legacy_id   BIGINT,
    new_id      UUID,
    PRIMARY KEY (table_name, legacy_id)
)
```

### B. 时间戳 Asia/Shanghai → UTC

```python
from datetime import timezone, timedelta
CST = timezone(timedelta(hours=8))

def to_utc(dt_naive):
    """V4 存储的 naive datetime 视为 CST,转 UTC."""
    return dt_naive.replace(tzinfo=CST).astimezone(timezone.utc)
```

### C. 中文计量单位 → UnitOfMeasure 枚举

| V4 中文 | V5 枚举 |
|---------|---------|
| 件 / 个 | `pcs` |
| 千克 / kg | `kg` |
| 克 / g | `g` |
| 升 / L | `L` |
| 米 / m | `m` |
| 小时 | `h` |
| 千瓦时 | `kWh` |

未匹配的单位应记录到 `_unmapped_uom.csv` 待人工处理。

### D. 单据状态映射

| V4 状态 (典型) | V5 DocumentStatus |
|----------------|-------------------|
| 0 / 草稿 / draft | `draft` |
| 1 / 待审 / pending | `submitted` |
| 2 / 已审 / approved | `approved` |
| 3 / 驳回 / rejected | `rejected` |
| 4 / 作废 / void | `cancelled` |
| 5 / 完成 / done | `closed` |

### E. 金额精度

V4 通常为 `DECIMAL(18,2)`,V5 为 `DECIMAL(18,4)`。迁移时小数位扩展,不会丢失精度。

### F. 多租户 tenant_id

V4 可能无多租户概念。ETL 时统一赋一个默认 `tenant_id`,或按 V4 的 `company_id` 字段映射。

---

## 待确认事项 (拿到真实 dump 后核对)

1. [ ] V4 供应商评分是否独立表还是字段在 `t_supplier` 上
2. [ ] V4 库位层级实际有几级
3. [ ] V4 出入库是否真的分两张表 (`t_stock_in` / `t_stock_out`) 还是合一张
4. [ ] V4 采购申请 (PR) 是否存在,还是直接从 PO 开始
5. [ ] V4 `unit` 字段的实际取值列表 (中文/英文/混合)
6. [ ] V4 状态字段是数字编码还是字符串
7. [ ] V4 是否有 RFQ (询价单) 表
8. [ ] V4 税率/税额字段的具体精度
9. [ ] V4 多币种支持情况
10. [ ] V4 批次号 / 有效期管理的覆盖范围

---

## ETL 执行顺序 (依赖关系)

```
1. t_warehouse        → scm.warehouse          (无依赖)
2. t_warehouse_location → scm.location          (依赖 warehouse)
3. t_supplier         → scm.supplier            (无依赖)
4. t_supplier_score   → scm.supplier_rating     (依赖 supplier)
5. t_purchase_request → scm.purchase_request    (依赖 supplier, product*)
6. t_purchase_order   → scm.purchase_order      (依赖 supplier, product*)
7. t_purchase_receipt → scm.purchase_receipt     (依赖 PO, warehouse)
8. t_inventory        → scm.inventory           (依赖 product*, warehouse, location)
9. t_stock_in/out     → scm.stock_move          (依赖 product*, warehouse, location)
10. t_stocktake       → scm.stocktake           (依赖 warehouse)

* product 来自 Lane 1 (plm),需先完成 Lane 1 的产品迁移或提供 product legacy_id_map
```

---

## 数据校验 (Reconciliation)

ETL 完成后对每个租户执行:

| 校验项 | 方法 |
|--------|------|
| 行数一致 | `COUNT(*)` V4 vs V5 每张表 |
| 金额一致 | `SUM(total_amount)` 采购订单 |
| 库存一致 | `SUM(quantity)` 按仓库按物料 |
| 流水平衡 | 入库总量 - 出库总量 ≈ 当前库存 |
| 外键完整 | V5 所有 FK 引用的 UUID 在目标表中存在 |
| 无孤儿记录 | 明细行的 header_id 都能关联到表头 |
