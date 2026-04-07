"""Tests for TASK-PLM-003: CAD attachment upload to MinIO."""

from __future__ import annotations

import hashlib
import io
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


def _create_product(auth_client: Any, code: str = "CAD-P") -> dict[str, Any]:
    r = auth_client.post(
        "/plm/products",
        json={"code": code, "name": "CAD Product", "category": "self_made", "uom": "pcs"},
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def mock_minio() -> Any:
    """Mock MinIO client so tests don't need a running MinIO."""
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = True
    with patch(
        "packages.product_lifecycle.services.cad_service.upload_cad",
        wraps=None,
    ) as _:
        # Actually, we want to mock the minio_client module functions
        pass
    # Patch at the minio_client module level
    with (
        patch(
            "packages.product_lifecycle.services.minio_client.get_minio_client",
            return_value=mock_client,
        ),
        patch(
            "packages.product_lifecycle.services.minio_client.upload_cad_file",
            return_value="fake/key",
        ) as mock_upload,
    ):
        yield mock_upload


class TestUploadCAD:
    def test_upload_success(self, auth_client: Any, mock_minio: Any) -> None:
        prod = _create_product(auth_client)
        pid = prod["id"]
        tid = prod["tenant_id"]

        file_content = b"fake CAD binary data for testing"
        expected_checksum = hashlib.md5(file_content).hexdigest()  # noqa: S324

        r = auth_client.post(
            f"/plm/products/{pid}/cad",
            files={"file": ("drawing.dwg", io.BytesIO(file_content), "application/acad")},
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["product_id"] == pid
        assert data["version"] == "V1.0"
        assert data["filename"] == "drawing.dwg"
        assert data["object_key"] == f"{tid}/{pid}/V1.0/drawing.dwg"
        assert data["content_type"] == "application/acad"
        assert data["file_size"] == len(file_content)
        assert data["checksum"] == expected_checksum

    def test_upload_requires_auth(self, client: Any) -> None:
        fake_id = "00000000-0000-0000-0000-000000000001"
        r = client.post(
            f"/plm/products/{fake_id}/cad",
            files={"file": ("test.dwg", io.BytesIO(b"data"), "application/octet-stream")},
        )
        assert r.status_code == 401

    def test_upload_product_not_found(self, auth_client: Any, mock_minio: Any) -> None:
        fake_id = "00000000-0000-0000-0000-000000000099"
        r = auth_client.post(
            f"/plm/products/{fake_id}/cad",
            files={"file": ("test.dwg", io.BytesIO(b"data"), "application/octet-stream")},
        )
        assert r.status_code == 404

    def test_upload_empty_file_rejected(self, auth_client: Any, mock_minio: Any) -> None:
        prod = _create_product(auth_client)
        r = auth_client.post(
            f"/plm/products/{prod['id']}/cad",
            files={"file": ("empty.dwg", io.BytesIO(b""), "application/octet-stream")},
        )
        assert r.status_code == 400

    def test_upload_uses_current_version(self, auth_client: Any, mock_minio: Any) -> None:
        """上传文件时应使用产品的当前版本。"""
        prod = _create_product(auth_client, code="CAD-VER")
        pid = prod["id"]

        # Bump to V2.0
        auth_client.post(f"/plm/products/{pid}/versions", json={})

        r = auth_client.post(
            f"/plm/products/{pid}/cad",
            files={"file": ("v2.dwg", io.BytesIO(b"v2 data"), "application/octet-stream")},
        )
        assert r.status_code == 201
        assert r.json()["version"] == "V2.0"
        assert "/V2.0/" in r.json()["object_key"]


class TestListCAD:
    def test_list_empty(self, auth_client: Any) -> None:
        prod = _create_product(auth_client, code="CAD-EMPTY")
        r = auth_client.get(f"/plm/products/{prod['id']}/cad")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_after_upload(self, auth_client: Any, mock_minio: Any) -> None:
        prod = _create_product(auth_client, code="CAD-LIST")
        pid = prod["id"]

        auth_client.post(
            f"/plm/products/{pid}/cad",
            files={"file": ("a.dwg", io.BytesIO(b"aaa"), "application/acad")},
        )
        auth_client.post(
            f"/plm/products/{pid}/cad",
            files={"file": ("b.step", io.BytesIO(b"bbb"), "model/step")},
        )

        r = auth_client.get(f"/plm/products/{pid}/cad")
        assert r.status_code == 200
        items = r.json()
        assert len(items) == 2
        filenames = {it["filename"] for it in items}
        assert filenames == {"a.dwg", "b.step"}

    def test_list_isolated_by_product(self, auth_client: Any, mock_minio: Any) -> None:
        """不同产品的 CAD 附件不互相干扰。"""
        p1 = _create_product(auth_client, code="ISO-1")
        p2 = _create_product(auth_client, code="ISO-2")

        auth_client.post(
            f"/plm/products/{p1['id']}/cad",
            files={"file": ("p1.dwg", io.BytesIO(b"p1"), "application/acad")},
        )
        auth_client.post(
            f"/plm/products/{p2['id']}/cad",
            files={"file": ("p2.dwg", io.BytesIO(b"p2"), "application/acad")},
        )

        r1 = auth_client.get(f"/plm/products/{p1['id']}/cad")
        r2 = auth_client.get(f"/plm/products/{p2['id']}/cad")
        assert len(r1.json()) == 1
        assert len(r2.json()) == 1
        assert r1.json()[0]["filename"] == "p1.dwg"
        assert r2.json()[0]["filename"] == "p2.dwg"
