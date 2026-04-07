#!/usr/bin/env python3
"""模拟前端新建表单 — 测试全部 18 个录入功能"""
from uuid import uuid4
import httpx

B = "http://localhost:8000"
c = httpx.Client(timeout=30)
r = c.post(f"{B}/auth/login", json={"tenant_code": "demo", "username": "admin", "password": "admin123"})
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
me = c.get(f"{B}/auth/me", headers=h).json()
tid, uid = me["tenant_id"], me["id"]

# Load reference IDs
prods = c.get(f"{B}/plm/products?skip=0&limit=1", headers=h).json()
pid = prods["items"][0]["id"]
custs = c.get(f"{B}/plm/customers", headers=h).json()
cid = custs[0]["id"]
sups = c.get(f"{B}/scm/suppliers?tenant_id={tid}&skip=0&limit=1", headers=h).json()
sid = sups["items"][0]["id"]
whs = c.get(f"{B}/scm/warehouses?tenant_id={tid}&skip=0&limit=1", headers=h).json()
wid = whs["items"][0]["id"]
emps = c.get(f"{B}/mgmt/hr/employees", headers=h).json()
eid = emps[0]["id"]
accts = c.get(f"{B}/mgmt/finance/accounts", headers=h).json()
a1, a2 = accts[0]["id"], accts[1]["id"]
wos = c.get(f"{B}/mfg/work-orders", headers=h).json()
wo_items = wos.get("items", wos) if isinstance(wos, dict) else wos
woid = wo_items[0]["id"] if wo_items else str(uuid4())

ok = fail = 0
results = []

def test(name, method, path, data, params=None):
    global ok, fail
    if method == "POST":
        r = c.post(f"{B}{path}", headers=h, json=data, params=params)
    else:
        r = c.get(f"{B}{path}", headers=h, params=params)
    if r.status_code < 400:
        ok += 1
        results.append(("✅", name, ""))
        print(f"  ✅ {name}")
    else:
        fail += 1
        detail = ""
        try:
            d = r.json()
            detail = d.get("detail", "")
            if isinstance(detail, list):
                detail = "; ".join(x.get("msg", "") for x in detail[:2])
        except:
            detail = r.text[:80]
        results.append(("❌", name, f"HTTP {r.status_code}: {detail}"))
        print(f"  ❌ {name} ({r.status_code}): {detail}")

u = uuid4().hex[:6]

print("═══════════════════════════════════════════")
print("  模拟前端新建表单测试 (18项)")
print("═══════════════════════════════════════════\n")

print("── PLM ──")
test("01 新建产品", "POST", "/plm/products",
     {"code": f"TP-{u}", "name": "测试新建产品", "category": "self_made", "uom": "pcs"})

test("02 新建客户", "POST", "/plm/customers",
     {"code": f"TC-{u}", "name": "测试新建客户", "kind": "b2b", "rating": "B"})

test("03 新建ECN", "POST", "/plm/ecn",
     {"product_id": pid, "ecn_no": f"ECN-T{u}", "title": "测试工程变更", "reason": "质量改进"})

test("04 新建售后工单", "POST", "/plm/service/tickets",
     {"customer_id": cid, "ticket_no": f"SVC-T{u}", "description": "测试售后问题"})

print("\n── MFG ──")
test("05 新建质检记录", "POST", "/mfg/qc/inspections",
     {"inspection_no": f"QC-T{u}", "type": "oqc", "product_id": pid,
      "sample_size": 50, "defect_count": 1, "result": "pass", "inspector_id": uid})

test("06 新建安全隐患", "POST", "/mfg/safety/hazards",
     {"hazard_no": f"HAZ-T{u}", "location": "CNC加工区", "level": "minor", "description": "测试隐患"})

test("07 新建设备", "POST", "/mfg/equipment",
     {"code": f"EQ-T{u}", "name": "测试设备", "workshop_id": str(uuid4()), "status": "running"})

test("08 新建报工", "POST", "/mfg/job-tickets",
     {"work_order_id": woid, "ticket_no": f"JT-T{u}"})

print("\n── SCM ──")
test("09 新建供应商", "POST", "/scm/suppliers",
     {"code": f"TS-{u}", "name": "测试新建供应商", "tier": "approved"},
     params={"tenant_id": tid})

test("10 新建采购单", "POST", "/scm/purchase-orders",
     {"order_no": f"PO-T{u}", "supplier_id": sid,
      "lines": [{"product_id": pid, "quantity": 100, "uom": "pcs", "unit_price": 25.50}]},
     params={"tenant_id": tid})

test("11 新建仓库", "POST", "/scm/warehouses",
     {"code": f"TWH-{u}", "name": "测试仓库", "address": "测试地址"},
     params={"tenant_id": tid})

test("12 入库操作", "POST", "/scm/receive",
     {"product_id": pid, "quantity": 200, "uom": "pcs", "warehouse_id": wid, "batch_no": f"BT-{u}"},
     params={"tenant_id": tid})

test("13 新建盘点", "POST", "/scm/stocktakes",
     {"stocktake_no": f"ST-T{u}", "warehouse_id": wid,
      "lines": [{"product_id": pid, "actual_quantity": 180, "uom": "pcs"}]},
     params={"tenant_id": tid})

print("\n── MGMT ──")
test("14 新建GL科目", "POST", "/mgmt/finance/accounts",
     {"code": f"T{u}", "name": "测试科目", "account_type": "ASSET", "level": 1})

test("15 新建记账凭证", "POST", "/mgmt/finance/journal",
     {"entry_date": "2026-04-07", "memo": "测试凭证",
      "lines": [
          {"account_id": a1, "debit_amount": 5000, "credit_amount": 0},
          {"account_id": a2, "debit_amount": 0, "credit_amount": 5000},
      ]})

test("16 新建员工", "POST", "/mgmt/hr/employees",
     {"employee_no": f"TE-{u}", "name": "测试员工", "position": "测试岗", "base_salary": 8000})

test("17 新建考勤", "POST", "/mgmt/hr/attendance",
     {"employee_id": eid, "work_date": "2026-04-08",
      "clock_in": "08:30:00", "clock_out": "17:30:00",
      "status": "normal", "work_hours": 9, "overtime_hours": 0})

test("18 发起审批", "POST", "/mgmt/approval",
     {"business_type": "expense_claim", "business_id": str(uuid4()),
      "payload": {"reason": "测试费用报销", "amount": 3500}})

print(f"\n{'='*43}")
print(f"  结果: {ok} 通过 / {fail} 失败 / 18 总计")
print(f"{'='*43}")

if fail:
    print("\n失败详情:")
    for icon, name, detail in results:
        if icon == "❌":
            print(f"  {name}: {detail}")
