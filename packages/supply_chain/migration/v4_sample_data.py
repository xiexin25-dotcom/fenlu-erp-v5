"""
V4 模拟数据生成器
==================

生成符合 V4 典型 ERP 采购/仓储模块格式的 CSV 文件。
用于 ETL 测试和 dry-run 验证。

调用 generate_all() 返回 dict[table_name, list[dict]] 形式的内存数据,
或 write_csvs(output_dir) 写到磁盘。
"""

from __future__ import annotations

import csv
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# ------------------------------------------------------------------ #
# V4 模拟数据 (Asia/Shanghai naive datetimes, INT PKs, 中文单位)
# ------------------------------------------------------------------ #

_SUPPLIERS = [
    {"id": 1, "supplier_code": "SUP-001", "supplier_name": "华东螺栓厂",
     "contact_person": "张三", "phone": "13800001111", "address": "上海市浦东新区",
     "bank_account": "6222021234567890", "tax_no": "91310000MA1K1234X",
     "level": 1, "score": 92.5, "is_active": 1,
     "create_time": "2024-01-15 08:30:00", "update_time": "2025-11-20 14:00:00"},
    {"id": 2, "supplier_code": "SUP-002", "supplier_name": "南方五金供应链",
     "contact_person": "李四", "phone": "13900002222", "address": "广州市天河区",
     "bank_account": "6222029876543210", "tax_no": "91440000MA5D5678Y",
     "level": 2, "score": 78.0, "is_active": 1,
     "create_time": "2024-03-01 09:00:00", "update_time": "2025-12-01 10:00:00"},
    {"id": 3, "supplier_code": "SUP-003", "supplier_name": "废旧供应商",
     "contact_person": "王五", "phone": "13700003333", "address": "北京市朝阳区",
     "bank_account": "", "tax_no": "",
     "level": 4, "score": 15.0, "is_active": 0,
     "create_time": "2023-06-01 10:00:00", "update_time": "2025-01-01 00:00:00"},
]

_WAREHOUSES = [
    {"id": 1, "warehouse_code": "WH-01", "warehouse_name": "主仓库",
     "address": "上海市嘉定区", "manager_id": 100, "is_active": 1,
     "create_time": "2023-01-01 00:00:00"},
    {"id": 2, "warehouse_code": "WH-02", "warehouse_name": "原材料仓",
     "address": "上海市嘉定区B栋", "manager_id": 101, "is_active": 1,
     "create_time": "2023-01-01 00:00:00"},
]

_WAREHOUSE_LOCATIONS = [
    {"id": 1, "warehouse_id": 1, "location_code": "Z-A", "location_name": "A区",
     "parent_id": None, "level": 1, "is_active": 1},
    {"id": 2, "warehouse_id": 1, "location_code": "A-A01", "location_name": "A区1通道",
     "parent_id": 1, "level": 2, "is_active": 1},
    {"id": 3, "warehouse_id": 2, "location_code": "Z-B", "location_name": "B区",
     "parent_id": None, "level": 1, "is_active": 1},
]

_PURCHASE_ORDERS = [
    {"id": 1, "order_no": "PO-2025-0001", "supplier_id": 1, "status": 2,
     "total_amount": 25000.00, "currency": "CNY",
     "expected_date": "2025-04-01", "buyer_id": 100,
     "create_time": "2025-03-01 09:00:00", "update_time": "2025-03-05 14:00:00"},
    {"id": 2, "order_no": "PO-2025-0002", "supplier_id": 2, "status": 5,
     "total_amount": 8600.50, "currency": "CNY",
     "expected_date": "2025-04-15", "buyer_id": 101,
     "create_time": "2025-03-10 10:00:00", "update_time": "2025-04-20 16:00:00"},
    {"id": 3, "order_no": "PO-2025-0003", "supplier_id": 1, "status": 0,
     "total_amount": 1200.00, "currency": "CNY",
     "expected_date": None, "buyer_id": 100,
     "create_time": "2025-06-01 08:00:00", "update_time": "2025-06-01 08:00:00"},
]

_PURCHASE_ORDER_DETAILS = [
    {"id": 1, "order_id": 1, "material_id": 1001, "quantity": 1000.0,
     "unit": "件", "unit_price": 25.00, "amount": 25000.00,
     "received_qty": 800.0, "tax_rate": 13.00, "tax_amount": 3250.00},
    {"id": 2, "order_id": 2, "material_id": 1002, "quantity": 500.0,
     "unit": "千克", "unit_price": 17.201, "amount": 8600.50,
     "received_qty": 500.0, "tax_rate": 13.00, "tax_amount": 1118.065},
    {"id": 3, "order_id": 3, "material_id": 1001, "quantity": 100.0,
     "unit": "件", "unit_price": 12.00, "amount": 1200.00,
     "received_qty": 0.0, "tax_rate": 13.00, "tax_amount": 156.00},
]

_INVENTORY = [
    {"id": 1, "material_id": 1001, "warehouse_id": 1, "location_id": 2,
     "quantity": 800.0, "available_qty": 700.0, "locked_qty": 100.0,
     "in_transit_qty": 0.0, "unit": "件", "batch_no": "B2025-001",
     "expiry_date": None, "safety_stock": 200.0,
     "update_time": "2025-04-10 09:00:00"},
    {"id": 2, "material_id": 1002, "warehouse_id": 2, "location_id": 3,
     "quantity": 500.0, "available_qty": 500.0, "locked_qty": 0.0,
     "in_transit_qty": 50.0, "unit": "千克", "batch_no": "B2025-002",
     "expiry_date": "2026-06-30", "safety_stock": 100.0,
     "update_time": "2025-04-20 16:00:00"},
]

_STOCK_IN = [
    {"id": 1, "bill_no": "IN-2025-001", "material_id": 1001,
     "quantity": 800.0, "unit": "件", "warehouse_id": 1, "location_id": 2,
     "ref_type": "purchase", "ref_id": 1, "operator_id": 100,
     "operate_time": "2025-04-01 14:00:00", "remark": "采购入库"},
    {"id": 2, "bill_no": "IN-2025-002", "material_id": 1002,
     "quantity": 500.0, "unit": "千克", "warehouse_id": 2, "location_id": 3,
     "ref_type": "purchase", "ref_id": 2, "operator_id": 101,
     "operate_time": "2025-04-16 10:00:00", "remark": "采购入库"},
]

_STOCK_OUT = [
    {"id": 1, "bill_no": "OUT-2025-001", "material_id": 1001,
     "quantity": 50.0, "unit": "件", "warehouse_id": 1, "location_id": 2,
     "ref_type": "produce", "ref_id": 5001, "operator_id": 102,
     "operate_time": "2025-04-05 08:30:00", "remark": "生产领料"},
]

_STOCKTAKES = [
    {"id": 1, "stocktake_no": "ST-2025-001", "warehouse_id": 1,
     "status": 2, "stocktake_date": "2025-05-01",
     "operator_id": 100, "create_time": "2025-05-01 08:00:00"},
]

_STOCKTAKE_DETAILS = [
    {"id": 1, "stocktake_id": 1, "material_id": 1001,
     "system_qty": 750.0, "actual_qty": 748.0, "variance_qty": -2.0,
     "remark": "少2件"},
]


def generate_all() -> dict[str, list[dict]]:
    """返回所有 V4 模拟数据,key=表名, value=行列表。"""
    return {
        "t_supplier": _SUPPLIERS,
        "t_warehouse": _WAREHOUSES,
        "t_warehouse_location": _WAREHOUSE_LOCATIONS,
        "t_purchase_order": _PURCHASE_ORDERS,
        "t_purchase_order_detail": _PURCHASE_ORDER_DETAILS,
        "t_inventory": _INVENTORY,
        "t_stock_in": _STOCK_IN,
        "t_stock_out": _STOCK_OUT,
        "t_stocktake": _STOCKTAKES,
        "t_stocktake_detail": _STOCKTAKE_DETAILS,
    }


def write_csvs(output_dir: str | Path) -> dict[str, Path]:
    """将模拟数据写为 CSV 文件,返回 {表名: 文件路径}。"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for table_name, rows in generate_all().items():
        if not rows:
            continue
        fp = output_dir / f"{table_name}.csv"
        with open(fp, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        paths[table_name] = fp
    return paths
