"""Foundation 端到端测试。

如果这个文件全部 PASS,foundation 就是健康的。Lane 的开发可以放心进行。
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_login_success(client: TestClient, seed_admin: dict) -> None:
    r = client.post(
        "/auth/login",
        json={
            "tenant_code": seed_admin["tenant_code"],
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "Bearer"


def test_login_wrong_password(client: TestClient, seed_admin: dict) -> None:
    r = client.post(
        "/auth/login",
        json={
            "tenant_code": seed_admin["tenant_code"],
            "username": seed_admin["username"],
            "password": "WRONG",
        },
    )
    assert r.status_code == 401


def test_login_unknown_tenant(client: TestClient) -> None:
    r = client.post(
        "/auth/login",
        json={"tenant_code": "ghost", "username": "x", "password": "y"},
    )
    assert r.status_code == 401


def test_me_requires_auth(client: TestClient) -> None:
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_me_with_token(auth_client: TestClient, seed_admin: dict) -> None:
    r = auth_client.get("/auth/me")
    assert r.status_code == 200
    me = r.json()
    assert me["username"] == seed_admin["username"]
    assert me["is_superuser"] is True


def test_refresh_token(client: TestClient, seed_admin: dict) -> None:
    login = client.post(
        "/auth/login",
        json={
            "tenant_code": seed_admin["tenant_code"],
            "username": seed_admin["username"],
            "password": seed_admin["password"],
        },
    ).json()
    r = client.post("/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "Bearer"


def test_orgs_list_empty(auth_client: TestClient) -> None:
    r = auth_client.get("/orgs")
    assert r.status_code == 200
    assert r.json() == []


def test_orgs_requires_auth(client: TestClient) -> None:
    r = client.get("/orgs")
    assert r.status_code == 401
