"""操作日志 — 所有写操作留痕。"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db.base import Base


class AuditLog(Base):
    """全局操作日志表，记录每一次写操作。"""

    __tablename__ = "audit_logs"
    __table_args__ = {"schema": "public"}

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(PgUUID(as_uuid=True), nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="冗余用户名")
    method: Mapped[str] = mapped_column(String(10), nullable=False, comment="HTTP方法")
    path: Mapped[str] = mapped_column(String(512), nullable=False, comment="请求路径")
    status_code: Mapped[int] = mapped_column(nullable=False, comment="响应状态码")
    resource: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="资源类型(如plm.product)")
    action: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="操作(create/update/delete/transition)")
    detail: Mapped[str | None] = mapped_column(Text, nullable=True, comment="操作摘要")
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
