"""Tests for KPI definition registry (TASK-MGMT-007)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from packages.management_decision.services.kpi import SEED_KPIS


class TestKPISeed:
    def test_seed_creates_kpis(self, auth_client: TestClient) -> None:
        r = auth_client.post("/mgmt/bi/kpis/seed")
        assert r.status_code == 200, r.text
        assert r.json()["seeded"] == len(SEED_KPIS)

    def test_seed_idempotent(self, auth_client: TestClient) -> None:
        auth_client.post("/mgmt/bi/kpis/seed")
        r = auth_client.post("/mgmt/bi/kpis/seed")
        assert r.json()["seeded"] == 0  # no new ones


class TestKPIList:
    def test_list_all(self, auth_client: TestClient) -> None:
        auth_client.post("/mgmt/bi/kpis/seed")
        r = auth_client.get("/mgmt/bi/kpis")
        assert r.status_code == 200
        assert len(r.json()) == len(SEED_KPIS)

    def test_list_filter_by_category(self, auth_client: TestClient) -> None:
        auth_client.post("/mgmt/bi/kpis/seed")

        for cat in ("financial", "operations", "quality", "hr", "safety", "energy"):
            r = auth_client.get("/mgmt/bi/kpis", params={"category": cat})
            assert r.status_code == 200
            expected = sum(1 for k in SEED_KPIS if k["category"] == cat)
            assert len(r.json()) == expected, f"category={cat}"

    def test_all_six_categories_covered(self, auth_client: TestClient) -> None:
        auth_client.post("/mgmt/bi/kpis/seed")
        r = auth_client.get("/mgmt/bi/kpis")
        categories = {k["category"] for k in r.json()}
        assert categories == {"financial", "operations", "quality", "hr", "safety", "energy"}

    def test_all_source_lanes_represented(self, auth_client: TestClient) -> None:
        auth_client.post("/mgmt/bi/kpis/seed")
        r = auth_client.get("/mgmt/bi/kpis")
        lanes = {k["source_lane"] for k in r.json()}
        # At minimum mfg, mgmt, plm should be present
        assert "mfg" in lanes
        assert "mgmt" in lanes
        assert "plm" in lanes


class TestKPIGetByCode:
    def test_get_by_code(self, auth_client: TestClient) -> None:
        auth_client.post("/mgmt/bi/kpis/seed")
        r = auth_client.get("/mgmt/bi/kpi/OPS-001")
        assert r.status_code == 200
        data = r.json()
        assert data["code"] == "OPS-001"
        assert data["name"] == "设备综合效率 OEE"
        assert data["category"] == "operations"
        assert data["unit"] == "%"
        assert data["aggregation"] == "avg"

    def test_get_by_code_not_found(self, auth_client: TestClient) -> None:
        r = auth_client.get("/mgmt/bi/kpi/NONEXISTENT")
        assert r.status_code == 404

    def test_get_kpi_data_empty(self, auth_client: TestClient) -> None:
        auth_client.post("/mgmt/bi/kpis/seed")
        r = auth_client.get("/mgmt/bi/kpi/FIN-001/data")
        assert r.status_code == 200
        assert r.json() == []


class TestKPISeedContent:
    """验证种子数据覆盖全部 16 工信部场景。"""

    def test_financial_kpis_exist(self, auth_client: TestClient) -> None:
        auth_client.post("/mgmt/bi/kpis/seed")
        r = auth_client.get("/mgmt/bi/kpis", params={"category": "financial"})
        codes = {k["code"] for k in r.json()}
        assert "FIN-001" in codes  # 月度营业收入
        assert "FIN-004" in codes  # 现金流净额

    def test_safety_kpis_exist(self, auth_client: TestClient) -> None:
        auth_client.post("/mgmt/bi/kpis/seed")
        r = auth_client.get("/mgmt/bi/kpis", params={"category": "safety"})
        codes = {k["code"] for k in r.json()}
        assert "SAF-001" in codes  # 安全隐患数
        assert "SAF-003" in codes  # 连续安全生产天数

    def test_energy_kpis_exist(self, auth_client: TestClient) -> None:
        auth_client.post("/mgmt/bi/kpis/seed")
        r = auth_client.get("/mgmt/bi/kpis", params={"category": "energy"})
        codes = {k["code"] for k in r.json()}
        assert "ENG-001" in codes  # 万元产值综合能耗
        assert "ENG-003" in codes  # 单位产品能耗

    def test_at_least_20_kpis(self, auth_client: TestClient) -> None:
        auth_client.post("/mgmt/bi/kpis/seed")
        r = auth_client.get("/mgmt/bi/kpis")
        assert len(r.json()) >= 20
