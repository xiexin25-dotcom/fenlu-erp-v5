"""CAD attachment business logic: upload to MinIO + save metadata."""

from __future__ import annotations

import hashlib
from typing import BinaryIO, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.product_lifecycle.models import CadAttachment, Product


class MinIOUploader(Protocol):
    """Protocol for MinIO upload — allows test injection."""

    def __call__(
        self,
        *,
        object_key: str,
        data: BinaryIO,
        length: int,
        content_type: str,
    ) -> str: ...


async def upload_cad(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    product_id: UUID,
    filename: str,
    file_data: bytes,
    content_type: str,
    uploader: MinIOUploader | None = None,
) -> CadAttachment:
    """上传 CAD 文件到 MinIO 并保存元数据到 DB。"""
    # 确认 product 存在
    result = await session.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise ValueError("product not found")

    version = product.current_version
    object_key = f"{tenant_id}/{product_id}/{version}/{filename}"
    checksum = hashlib.md5(file_data).hexdigest()  # noqa: S324
    file_size = len(file_data)

    # Upload to MinIO
    if uploader is not None:
        import io

        uploader(
            object_key=object_key,
            data=io.BytesIO(file_data),
            length=file_size,
            content_type=content_type,
        )
    else:
        import io

        from packages.product_lifecycle.services.minio_client import (
            get_minio_client,
            upload_cad_file,
        )

        client = get_minio_client()
        upload_cad_file(
            client,
            object_key=object_key,
            data=io.BytesIO(file_data),
            length=file_size,
            content_type=content_type,
        )

    # Save metadata
    attachment = CadAttachment(
        tenant_id=tenant_id,
        product_id=product_id,
        version=version,
        filename=filename,
        object_key=object_key,
        content_type=content_type,
        file_size=file_size,
        checksum=checksum,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(attachment)
    await session.flush()
    return attachment


async def list_cad_attachments(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    product_id: UUID,
) -> list[CadAttachment]:
    result = await session.execute(
        select(CadAttachment)
        .where(
            CadAttachment.product_id == product_id,
            CadAttachment.tenant_id == tenant_id,
        )
        .order_by(CadAttachment.created_at.desc())
    )
    return list(result.scalars().all())
