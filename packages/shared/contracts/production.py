"""
Lane 2 · 生产执行 对外契约
==========================

本文件定义 Lane 2 (MES/QMS/EAM/EHS/能耗) 暴露给其他 lane 的 DTO。
**这是失分重灾区,5 个约束性场景的输出契约必须最早冻结。**

工信部场景: 计划排程 / 生产管控* / 质量管理* / 设备管理* / 安全生产* / 能耗管理*
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from pydantic import Field

from .base import BaseSchema, Quantity, TimestampMixin

# --------------------------------------------------------------------------- #
# 生产管控 · WorkOrder / 报工
# --------------------------------------------------------------------------- #


class WorkOrderStatus(StrEnum):
    PLANNED = "planned"
    RELEASED = "released"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CLOSED = "closed"


class WorkOrderDTO(BaseSchema, TimestampMixin):
    """工单,Lane 3 据此领料,Lane 4 据此核算成本。"""

    id: UUID
    order_no: str
    product_id: UUID
    bom_id: UUID
    routing_id: UUID
    planned_quantity: Quantity
    completed_quantity: Quantity
    scrap_quantity: Quantity
    status: WorkOrderStatus
    planned_start: datetime
    planned_end: datetime
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    sales_order_id: UUID | None = None  # 反查 Lane 1


class MaterialIssueRequest(BaseSchema):
    """Lane 2 → Lane 3 的领料请求 (POST /scm/issue)。"""

    work_order_id: UUID
    product_id: UUID
    quantity: Quantity
    requested_at: datetime
    requested_by: UUID


# --------------------------------------------------------------------------- #
# 质量管理
# --------------------------------------------------------------------------- #


class InspectionType(StrEnum):
    IQC = "iqc"  # 来料
    IPQC = "ipqc"  # 制程
    OQC = "oqc"  # 出货
    FAI = "fai"  # 首件


class InspectionResult(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    CONDITIONAL = "conditional"


class QCInspectionDTO(BaseSchema, TimestampMixin):
    id: UUID
    inspection_no: str
    type: InspectionType
    product_id: UUID
    work_order_id: UUID | None = None
    sample_size: int = Field(..., ge=1)
    defect_count: int = Field(..., ge=0)
    result: InspectionResult
    inspector_id: UUID


# --------------------------------------------------------------------------- #
# 设备管理
# --------------------------------------------------------------------------- #


class EquipmentStatus(StrEnum):
    RUNNING = "running"
    IDLE = "idle"
    MAINTENANCE = "maintenance"
    FAULT = "fault"
    OFFLINE = "offline"


class EquipmentSummary(BaseSchema, TimestampMixin):
    id: UUID
    code: str
    name: str
    workshop_id: UUID
    status: EquipmentStatus
    is_special_equipment: bool = False  # 特种设备需上报应急局


class OEERecordDTO(BaseSchema):
    """OEE = 可用率 × 性能率 × 良品率。Lane 4 BI 看板订阅。"""

    equipment_id: UUID
    record_date: date
    availability: float = Field(..., ge=0, le=1)
    performance: float = Field(..., ge=0, le=1)
    quality: float = Field(..., ge=0, le=1)
    oee: float = Field(..., ge=0, le=1)


# --------------------------------------------------------------------------- #
# 安全生产
# --------------------------------------------------------------------------- #


class HazardLevel(StrEnum):
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CRITICAL = "critical"


class HazardStatus(StrEnum):
    REPORTED = "reported"
    ASSIGNED = "assigned"
    RECTIFYING = "rectifying"
    VERIFIED = "verified"
    CLOSED = "closed"


class SafetyHazardDTO(BaseSchema, TimestampMixin):
    id: UUID
    hazard_no: str
    location: str
    level: HazardLevel
    status: HazardStatus
    reported_by: UUID
    rectified_at: datetime | None = None
    closed_at: datetime | None = None


# --------------------------------------------------------------------------- #
# 能耗管理 (TimescaleDB 时序)
# --------------------------------------------------------------------------- #


class EnergyType(StrEnum):
    ELECTRICITY = "electricity"
    WATER = "water"
    GAS = "gas"
    STEAM = "steam"
    COMPRESSED_AIR = "compressed_air"


class EnergyReadingDTO(BaseSchema):
    meter_id: UUID
    energy_type: EnergyType
    timestamp: datetime
    reading: float = Field(..., ge=0)
    delta: float = Field(..., ge=0, description="本周期消耗量")
    uom: str  # kWh / m3 / GJ


class UnitConsumptionDTO(BaseSchema):
    """单位产品能耗,工信部能耗场景三级硬指标。"""

    product_id: UUID
    period_start: date
    period_end: date
    energy_type: EnergyType
    total_consumption: float
    output_quantity: Quantity
    unit_consumption: float  # 总消耗 / 产量
