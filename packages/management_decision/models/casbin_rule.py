"""
Casbin 策略存储
================

存储 Casbin 的 p (policy) 和 g (role grouping) 规则。
Casbin adapter 从此表加载全量策略到内存。
"""

from __future__ import annotations

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from packages.shared.db.base import Base
from packages.shared.db.mixins import TimestampMixin, UUIDPKMixin

SCHEMA = "mgmt"


class CasbinRule(Base, UUIDPKMixin, TimestampMixin):
    """Casbin 规则行。

    ptype='p' → policy: (sub, dom, obj, act)
    ptype='g' → grouping: (user, role, domain)
    """

    __tablename__ = "casbin_rules"
    __table_args__ = (
        Index("ix_casbin_rules_ptype", "ptype"),
        {"schema": SCHEMA},
    )

    ptype: Mapped[str] = mapped_column(String(8), nullable=False, comment="p or g")
    v0: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    v1: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    v2: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    v3: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    v4: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    v5: Mapped[str] = mapped_column(String(256), nullable=False, default="")
