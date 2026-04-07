#!/usr/bin/env python3
"""填补缺失数据：安全隐患、AP/AR、KPI、工资、工位"""
import random
from datetime import datetime, timedelta
from uuid import uuid4
import httpx

B = "http://localhost:8000"
c = httpx.Client(timeout=30)

# Login
r = c.post(f"{B}/auth/login", json={"tenant_code": "demo", "username": "admin", "password": "admin123"})
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
me = c.get(f"{B}/auth/me", headers=h).json()
tid, uid = me["tenant_id"], me["id"]

ok = fail = 0
def post(path, data, params=None):
    global ok, fail
    r = c.post(f"{B}{path}", headers=h, json=data, params=params)
    if r.status_code < 400: ok += 1; return r.json()
    fail += 1; return None

# Load existing IDs
sup_r = c.get(f"{B}/scm/suppliers?tenant_id={tid}&skip=0&limit=50", headers=h).json()
sup_ids = [s["id"] for s in (sup_r.get("items", sup_r) if isinstance(sup_r, dict) else sup_r)]

prod_r = c.get(f"{B}/plm/products?skip=0&limit=50", headers=h).json()
prod_ids = [p["id"] for p in (prod_r.get("items", prod_r) if isinstance(prod_r, dict) else prod_r)]

acct_r = c.get(f"{B}/mgmt/finance/accounts", headers=h).json()
acct_items = acct_r if isinstance(acct_r, list) else acct_r.get("items", [])
acct_map = {a["code"]: a["id"] for a in acct_items}

emp_r = c.get(f"{B}/mgmt/hr/employees", headers=h).json()
emp_ids = [e["id"] for e in (emp_r if isinstance(emp_r, list) else emp_r.get("items", []))]

print("=== 1. 安全隐患 (60条, 跨12个月) ===")
locs = ["CNC加工区", "SMT车间", "冲压车间", "焊接区", "仓库通道", "配电房", "空压站", "化学品库"]
for i in range(60):
    post("/mfg/safety/hazards", {
        "hazard_no": f"HAZ-Y{uuid4().hex[:6]}",
        "location": random.choice(locs),
        "level": random.choices(["minor","moderate","major","critical"], weights=[50,30,15,5])[0],
        "description": f"年度巡检隐患#{i+1}",
    })
print(f"  {ok} ok, {fail} fail"); ok=fail=0

print("\n=== 2. AP 应付 (40条) ===")
for i in range(40):
    day = random.randint(0, 365)
    amt = round(random.uniform(5000, 200000), 2)
    post("/mgmt/finance/ap", {
        "purchase_order_id": str(uuid4()),
        "supplier_id": random.choice(sup_ids) if sup_ids else str(uuid4()),
        "total_amount": amt,
        "due_date": (datetime.now() - timedelta(days=day-30)).strftime("%Y-%m-%d"),
    })
print(f"  {ok} ok, {fail} fail"); ok=fail=0

print("\n=== 3. AR 应收 (40条) ===")
for i in range(40):
    day = random.randint(0, 365)
    post("/mgmt/finance/ar", {
        "sales_order_id": str(uuid4()),
        "customer_id": random.choice(prod_ids[:5]),
        "total_amount": round(random.uniform(10000, 500000), 2),
        "due_date": (datetime.now() - timedelta(days=day-60)).strftime("%Y-%m-%d"),
    })
print(f"  {ok} ok, {fail} fail"); ok=fail=0

print("\n=== 4. KPI 种子数据 ===")
post("/mgmt/bi/kpis/seed", {})
print(f"  {ok} ok, {fail} fail"); ok=fail=0

print("\n=== 5. 工资条 (12个月) ===")
for m in range(1, 13):
    r = c.post(f"{B}/mgmt/hr/payroll/run?period=2025-{m:02d}", headers=h)
    if r.status_code < 400: ok += 1
    else: fail += 1
for m in range(1, 5):
    r = c.post(f"{B}/mgmt/hr/payroll/run?period=2026-{m:02d}", headers=h)
    if r.status_code < 400: ok += 1
    else: fail += 1
print(f"  {ok} ok, {fail} fail"); ok=fail=0

print("\n=== 6. 工位 (6个) ===")
wid = str(uuid4())
for code, name, cap in [("WS-CNC","CNC工位",10),("WS-SMT","SMT工位",15),("WS-PRESS","冲压工位",12),
                         ("WS-WELD","焊接工位",8),("WS-ASSY","装配工位",20),("WS-TEST","测试工位",10)]:
    post("/mfg/aps/workstations", {"code": code, "name": name, "workshop_id": wid, "capacity": cap})
print(f"  {ok} ok, {fail} fail"); ok=fail=0

print("\n=== 完成! ===")
