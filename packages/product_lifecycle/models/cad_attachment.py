"""CadAttachment ORM model.

CAD 文件存储在 MinIO bucket plm-cad,本表只记录 object_key + 元数据。
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.shared.db import AuditMixin, Base, TenantMixin, TimestampMixin, UUIDPKMixin


class CadAttachment(UUIDPKMixin, TenantMixin, TimestampMixin, AuditMixin, Base):
    """CAD 附件元数据,实际文件在 MinIO。"""

    __tablename__ = "cad_attachments"
    __table_args__ = {"schema": "plm"}

    product_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("plm.products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    # relationships
    product: Mapped["packages.product_lifecycle.models.product.Product"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Product",
        lazy="selectin",
    )
