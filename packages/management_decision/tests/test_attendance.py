"""Tests for Attendance + payroll integration (TASK-MGMT-004)."""

from __future__ import annotations

from decimal import Decimal
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
    base_salary: str = "8700.0000",
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
    assert r.status_code == 201
    return r.json()


# --------------------------------------------------------------------------- #
# Attendance CRUD
# --------------------------------------------------------------------------- #


class TestAttendanceCRUD:
    def test_create_attendance(self, auth_client: TestClient) -> None:
        emp = _create_employee(auth_client)
        r = auth_client.post(
            "/mgmt/hr/attendance",
            json={
                "employee_id": emp["id"],
                "work_date": "2026-04-01",
                "clock_in": "08:30:00",
                "clock_out": "17:30:00",
                "status": "normal",
                "work_hours": "8.00",
                "overtime_hours": "0",
            },
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["status"] == "normal"
        assert data["work_date"] == "2026-04-01"

    def test_list_attendance(self, auth_client: TestClient) -> None:
        emp = _create_employee(auth_client)
        for day in range(1, 4):
            auth_client.post(
                "/mgmt/hr/attendance",
                json={
                    "employee_id": emp["id"],
                    "work_date": f"2026-04-{day:02d}",
                    "status": "normal",
                },
            )
        r = auth_client.get("/mgmt/hr/attendance", params={"employee_id": emp["id"]})
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_list_attendance_filter_by_date(self, auth_client: TestClient) -> None:
        emp = _create_employee(auth_client)
        for day in range(1, 6):
            auth_client.post(
                "/mgmt/hr/attendance",
                json={
                    "employee_id": emp["id"],
                    "work_date": f"2026-04-{day:02d}",
                },
            )
        r = auth_client.get(
            "/mgmt/hr/attendance",
            params={"date_from": "2026-04-03", "date_to": "2026-04-05"},
        )
        assert r.status_code == 200
        assert len(r.json()) == 3

    def test_get_attendance(self, auth_client: TestClient) -> None:
        emp = _create_employee(auth_client)
        r = auth_client.post(
            "/mgmt/hr/attendance",
            json={"employee_id": emp["id"], "work_date": "2026-04-01"},
        )
        rid = r.json()["id"]
        r2 = auth_client.get(f"/mgmt/hr/attendance/{rid}")
        assert r2.status_code == 200
        assert r2.json()["id"] == rid

    def test_get_attendance_not_found(self, auth_client: TestClient) -> None:
        r = auth_client.get(f"/mgmt/hr/attendance/{uuid4()}")
        assert r.status_code == 404


# --------------------------------------------------------------------------- #
# V4 ETL batch import
# --------------------------------------------------------------------------- #


class TestAttendanceImport:
    def test_import_batch(self, auth_client: TestClient) -> None:
        _create_employee(auth_client, employee_no="E01", name="甲")
        _create_employee(auth_client, employee_no="E02", name="乙")

        r = auth_client.post(
            "/mgmt/hr/attendance/import",
            json={
                "rows": [
                    {
                        "employee_no": "E01",
                        "work_date": "2026-04-01",
                        "clock_in": "08:00:00",
                        "clock_out": "17:00:00",
                        "status": "normal",
                    },
                    {
                        "employee_no": "E02",
                        "work_date": "2026-04-01",
                        "clock_in": "09:15:00",
                        "clock_out": "17:00:00",
                        "status": "late",
                    },
                    {
                        "employee_no": "E01",
                        "work_date": "2026-04-02",
                        "status": "absent",
                        "work_hours": "0",
                    },
                ]
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["imported"] == 3
        assert data["skipped"] == 0
        assert data["errors"] == []

    def test_import_skips_unknown_employee(self, auth_client: TestClient) -> None:
        _create_employee(auth_client, employee_no="E01", name="甲")

        r = auth_client.post(
            "/mgmt/hr/attendance/import",
            json={
                "rows": [
                    {"employee_no": "E01", "work_date": "2026-04-01"},
                    {"employee_no": "UNKNOWN", "work_date": "2026-04-01"},
                ]
            },
        )
        data = r.json()
        assert data["imported"] == 1
        assert data["skipped"] == 1
        assert len(data["errors"]) == 1
        assert "UNKNOWN" in data["errors"][0]

    def test_import_skips_duplicates(self, auth_client: TestClient) -> None:
        emp = _create_employee(auth_client, employee_no="E01", name="甲")
        # create one attendance directly
        auth_client.post(
            "/mgmt/hr/attendance",
            json={"employee_id": emp["id"], "work_date": "2026-04-01"},
        )

        r = auth_client.post(
            "/mgmt/hr/attendance/import",
            json={
                "rows": [
                    {"employee_no": "E01", "work_date": "2026-04-01"},  # dup
                    {"employee_no": "E01", "work_date": "2026-04-02"},  # new
                ]
            },
        )
        data = r.json()
        assert data["imported"] == 1
        assert data["skipped"] == 1


# --------------------------------------------------------------------------- #
# Payroll with attendance integration
# --------------------------------------------------------------------------- #


class TestPayrollWithAttendance:
    def test_payroll_calculates_overtime_and_deductions(
        self, auth_client: TestClient
    ) -> None:
        """员工月薪 8700, 加班 4 小时, 缺勤 1 天 → 验算 overtime_pay 和 deductions。"""
        emp = _create_employee(
            auth_client, employee_no="E01", name="测试员", base_salary="8700.0000"
        )
        emp_id = emp["id"]

        # 20 个正常工作日 + 2h overtime on day 1, 2h on day 10
        for day in range(1, 21):
            ot = "2.00" if day in (1, 10) else "0"
            auth_client.post(
                "/mgmt/hr/attendance",
                json={
                    "employee_id": emp_id,
                    "work_date": f"2026-04-{day:02d}",
                    "status": "normal",
                    "overtime_hours": ot,
                },
            )
        # 1 天缺勤
        auth_client.post(
            "/mgmt/hr/attendance",
            json={
                "employee_id": emp_id,
                "work_date": "2026-04-21",
                "status": "absent",
                "work_hours": "0",
            },
        )

        r = auth_client.post("/mgmt/hr/payroll/run", params={"period": "2026-04"})
        assert r.status_code == 201, r.text
        item = r.json()["items"][0]

        base = Decimal("8700")
        hourly = base / Decimal("21.75") / Decimal("8")
        expected_ot = (hourly * Decimal("1.5") * Decimal("4")).quantize(Decimal("0.0001"))
        daily = base / Decimal("21.75")
        expected_ded = (daily * 1).quantize(Decimal("0.0001"))
        expected_net = base + expected_ot - expected_ded

        assert Decimal(item["overtime_pay"]) == expected_ot
        assert Decimal(item["deductions"]) == expected_ded
        assert Decimal(item["net_pay"]) == expected_net

    def test_payroll_no_attendance_means_base_only(
        self, auth_client: TestClient
    ) -> None:
        """无考勤记录时 → overtime=0, deductions=0, net=base."""
        _create_employee(
            auth_client, employee_no="E01", name="新入职", base_salary="6000.0000"
        )

        r = auth_client.post("/mgmt/hr/payroll/run", params={"period": "2026-04"})
        assert r.status_code == 201
        item = r.json()["items"][0]
        assert float(item["overtime_pay"]) == 0
        assert float(item["deductions"]) == 0
        assert float(item["net_pay"]) == 6000
