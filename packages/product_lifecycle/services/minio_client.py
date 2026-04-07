"""MinIO client for PLM CAD attachments.

配置通过环境变量:
  MINIO_ENDPOINT   (default: localhost:9000)
  MINIO_ACCESS_KEY (default: minioadmin)
  MINIO_SECRET_KEY (default: minioadmin)
  MINIO_SECURE     (default: false)
"""

from __future__ import annotations

import os
from typing import BinaryIO

from minio import Minio

PLM_CAD_BUCKET = "plm-cad"

_client: Minio | None = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
            secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
            secure=os.getenv("MINIO_SECURE", "false").lower() == "true",
        )
    return _client


def ensure_bucket(client: Minio) -> None:
    if not client.bucket_exists(PLM_CAD_BUCKET):
        client.make_bucket(PLM_CAD_BUCKET)


def upload_cad_file(
    client: Minio,
    *,
    object_key: str,
    data: BinaryIO,
    length: int,
    content_type: str = "application/octet-stream",
) -> str:
    """上传文件到 MinIO,返回 object_key。"""
    ensure_bucket(client)
    client.put_object(
        PLM_CAD_BUCKET,
        object_key,
        data,
        length=length,
        content_type=content_type,
    )
    return object_key
