"""Tests for Employee + Payroll (TASK-MGMT-003)."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _create_employee(
    auth_client: TestClient,
    *,
    employee_no: str = "EMP001",
    name: str = "张三",
    base_salary: str = "8000.0000",
) -> dict:
    r = auth_client.post(
        "/mgmt/hr/employees",
        json={
            "employee_no": employee_no,
            "name": name,
            "position": "工程师",
            "base_salary": base_salary,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


# --------------------------------------------------------------------------- #
# Employee
# --------------------------------------------------------------------------- #


class TestEmployeeAPI:
    def test_create_employee(self, auth_client: TestClient) -> None:
        data = _create_employee(auth_client)
        assert data["employee_no"] == "EMP001"
        assert data["name"] == "张三"
        assert data["is_active"] is True
        assert float(data["base_salary"]) == 8000

    def test_list_employees(self, auth_client: TestClient) -> None:
        _create_employee(auth_client, employee_no="E01", name="甲")
        _create_employee(auth_client, employee_no="E02", name="乙")
        r = auth_client.get("/mgmt/hr/employees")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_get_employee(self, auth_client: TestClient) -> None:
        emp = _create_employee(auth_client)
        r = auth_client.get(f"/mgmt/hr/employees/{emp['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == emp["id"]

    def test_get_employee_not_found(self, auth_client: TestClient) -> None:
        r = auth_client.get(f"/mgmt/hr/employees/{uuid4()}")
        assert r.status_code == 404

    def test_update_employee(self, auth_client: TestClient) -> None:
        emp = _create_employee(auth_client)
        r = auth_client.patch(
            f"/mgmt/hr/employees/{emp['id']}",
            json={"position": "高级工程师", "base_salary": "12000.0000"},
        )
        assert r.status_code == 200
        assert r.json()["position"] == "高级工程师"
        assert float(r.json()["base_salary"]) == 12000

    def test_deactivate_employee(self, auth_client: TestClient) -> None:
        emp = _create_employee(auth_client)
        r = auth_client.patch(
            f"/mgmt/hr/employees/{emp['id']}",
            json={"is_active": False},
        )
        assert r.status_code == 200
        assert r.json()["is_active"] is False

        # active_only list should exclude
        r2 = auth_client.get("/mgmt/hr/employees")
        assert len(r2.json()) == 0

        # include inactive
        r3 = auth_client.get("/mgmt/hr/employees", params={"active_only": "false"})
        assert len(r3.json()) == 1


# --------------------------------------------------------------------------- #
# Payroll
# --------------------------------------------------------------------------- #


class TestPayrollAPI:
    def test_run_payroll(self, auth_client: TestClient) -> None:
        _create_employee(auth_client, employee_no="E01", name="甲", base_salary="8000.0000")
        _create_employee(auth_client, employee_no="E02", name="乙", base_salary="10000.0000")

        r = auth_client.post("/mgmt/hr/payroll/run", params={"period": "2026-04"})
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["period"] == "2026-04"
        assert data["status"] == "draft"
        assert data["head_count"] == 2
        assert float(data["total_amount"]) == 18000
        assert len(data["items"]) == 2

        # verify individual items
        items_by_no = {i["employee_no"]: i for i in data["items"]}
        assert float(items_by_no["E01"]["net_pay"]) == 8000
        assert float(items_by_no["E02"]["net_pay"]) == 10000

    def test_run_payroll_duplicate_period_422(self, auth_client: TestClient) -> None:
        _create_employee(auth_client, employee_no="E01", name="甲")
        auth_client.post("/mgmt/hr/payroll/run", params={"period": "2026-04"})

        r = auth_client.post("/mgmt/hr/payroll/run", params={"period": "2026-04"})
        assert r.status_code == 422
        assert "已存在" in r.json()["detail"]

    def test_run_payroll_no_employees_422(self, auth_client: TestClient) -> None:
        r = auth_client.post("/mgmt/hr/payroll/run", params={"period": "2026-04"})
        assert r.status_code == 422
        assert "没有在职员工" in r.json()["detail"]

    def test_run_payroll_excludes_inactive(self, auth_client: TestClient) -> None:
        emp1 = _create_employee(auth_client, employee_no="E01", name="在职", base_salary="5000")
        emp2 = _create_employee(auth_client, employee_no="E02", name="离职", base_salary="6000")
        # deactivate emp2
        auth_client.patch(f"/mgmt/hr/employees/{emp2['id']}", json={"is_active": False})

        r = auth_client.post("/mgmt/hr/payroll/run", params={"period": "2026-04"})
        assert r.status_code == 201
        assert r.json()["head_count"] == 1
        assert float(r.json()["total_amount"]) == 5000

    def test_list_payrolls(self, auth_client: TestClient) -> None:
        _create_employee(auth_client, employee_no="E01", name="甲")
        auth_client.post("/mgmt/hr/payroll/run", params={"period": "2026-03"})
        auth_client.post("/mgmt/hr/payroll/run", params={"period": "2026-04"})

        r = auth_client.get("/mgmt/hr/payroll")
        assert r.status_code == 200
        assert len(r.json()) == 2
        # desc order
        assert r.json()[0]["period"] == "2026-04"

    def test_get_payroll(self, auth_client: TestClient) -> None:
        _create_employee(auth_client, employee_no="E01", name="甲")
        r = auth_client.post("/mgmt/hr/payroll/run", params={"period": "2026-04"})
        pid = r.json()["id"]

        r2 = auth_client.get(f"/mgmt/hr/payroll/{pid}")
        assert r2.status_code == 200
        assert r2.json()["id"] == pid
        assert len(r2.json()["items"]) == 1

    def test_get_payroll_not_found(self, auth_client: TestClient) -> None:
        r = auth_client.get(f"/mgmt/hr/payroll/{uuid4()}")
        assert r.status_code == 404

    def test_run_payroll_bad_period_format(self, auth_client: TestClient) -> None:
        r = auth_client.post("/mgmt/hr/payroll/run", params={"period": "202604"})
        assert r.status_code == 422
