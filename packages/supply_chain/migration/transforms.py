"""
V4 → V5 公共转换函数
=====================

对应 MAPPING.md 中的 A~F 规则。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

CST = timezone(timedelta(hours=8))

# ------------------------------------------------------------------ #
# A. 主键 INT → UUID (legacy_id_map)
# ------------------------------------------------------------------ #


class LegacyIdMap:
    """维护 V4 INT → V5 UUID 的映射关系。"""

    def __init__(self) -> None:
        self._map: dict[tuple[str, int], UUID] = {}

    def get_or_create(self, table: str, legacy_id: int) -> UUID:
        key = (table, legacy_id)
        if key not in self._map:
            self._map[key] = uuid4()
        return self._map[key]

    def get(self, table: str, legacy_id: int) -> UUID | None:
        return self._map.get((table, legacy_id))

    def require(self, table: str, legacy_id: int) -> UUID:
        uid = self.get(table, legacy_id)
        if uid is None:
            raise ValueError(f"Missing legacy_id_map entry: {table}:{legacy_id}")
        return uid

    @property
    def entries(self) -> dict[tuple[str, int], UUID]:
        return dict(self._map)


# ------------------------------------------------------------------ #
# B. 时间戳 Asia/Shanghai → UTC
# ------------------------------------------------------------------ #


def to_utc(dt_str: str | None) -> datetime | None:
    """V4 naive datetime string (CST) → UTC-aware datetime。"""
    if not dt_str:
        return None
    dt = datetime.fromisoformat(dt_str)
    return dt.replace(tzinfo=CST).astimezone(timezone.utc)


def date_to_utc(date_str: str | None) -> datetime | None:
    """V4 DATE string → UTC-aware datetime at midnight。"""
    if not date_str:
        return None
    dt = datetime.fromisoformat(date_str)
    if dt.hour == 0 and dt.minute == 0:
        dt = dt.replace(hour=0, minute=0, second=0)
    return dt.replace(tzinfo=CST).astimezone(timezone.utc)


# ------------------------------------------------------------------ #
# C. 中文计量单位 → UnitOfMeasure 枚举
# ------------------------------------------------------------------ #

UOM_MAP: dict[str, str] = {
    "件": "pcs", "个": "pcs",
    "千克": "kg", "kg": "kg",
    "克": "g", "g": "g",
    "升": "L", "L": "L",
    "米": "m", "m": "m",
    "小时": "h", "h": "h",
    "千瓦时": "kWh", "kWh": "kWh",
    # English passthrough
    "pcs": "pcs",
}


def map_uom(v4_unit: str) -> str:
    """V4 单位 → V5 UnitOfMeasure 枚举值。"""
    return UOM_MAP.get(v4_unit.strip(), "pcs")


# ------------------------------------------------------------------ #
# D. 单据状态映射
# ------------------------------------------------------------------ #

STATUS_MAP: dict[str | int, str] = {
    0: "draft", "0": "draft", "草稿": "draft", "draft": "draft",
    1: "submitted", "1": "submitted", "待审": "submitted", "pending": "submitted",
    2: "approved", "2": "approved", "已审": "approved", "approved": "approved",
    3: "rejected", "3": "rejected", "驳回": "rejected", "rejected": "rejected",
    4: "cancelled", "4": "cancelled", "作废": "cancelled", "void": "cancelled",
    5: "closed", "5": "closed", "完成": "closed", "done": "closed",
}


def map_status(v4_status: str | int) -> str:
    return STATUS_MAP.get(v4_status, "draft")


# ------------------------------------------------------------------ #
# E. Supplier tier 映射
# ------------------------------------------------------------------ #

TIER_MAP: dict[int, str] = {
    1: "strategic",
    2: "preferred",
    3: "approved",
    4: "blacklisted",
}


def map_tier(v4_level: int) -> str:
    return TIER_MAP.get(int(v4_level), "approved")


# ------------------------------------------------------------------ #
# F. StockMove type 映射
# ------------------------------------------------------------------ #

STOCK_IN_TYPE_MAP: dict[str, str] = {
    "purchase": "purchase_receipt",
    "produce": "production_receipt",
    "transfer": "transfer",
    "adjust": "adjustment_in",
}

STOCK_OUT_TYPE_MAP: dict[str, str] = {
    "sale": "sales_issue",
    "produce": "production_issue",
    "transfer": "transfer",
    "adjust": "adjustment_out",
    "scrap": "scrap",
}
