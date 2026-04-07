#!/usr/bin/env python3
"""Fill remaining empty pages: service tickets, job tickets, POs, inventory-related"""
import random
from datetime import datetime, timedelta
from uuid import uuid4
import httpx

B = "http://localhost:8000"
c = httpx.Client(timeout=30)
r = c.post(f"{B}/auth/login", json={"tenant_code": "demo", "username": "admin", "password": "admin123"})
token = r.json()["access_token"]
h = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
me = c.get(f"{B}/auth/me", headers=h).json()
tid = me["tenant_id"]

ok = fail = 0
def post(path, data, params=None):
    global ok, fail
    r = c.post(f"{B}{path}", headers=h, json=data, params=params)
    if r.status_code < 400: ok += 1; return r.json()
    else: fail += 1; return None

# Load IDs
prods = c.get(f"{B}/plm/products?skip=0&limit=50", headers=h).json()
prod_ids = [p["id"] for p in prods.get("items", prods)]

custs = c.get(f"{B}/plm/customers", headers=h).json()
cust_ids = [c_["id"] for c_ in (custs if isinstance(custs, list) else custs.get("items", []))]

sups = c.get(f"{B}/scm/suppliers?tenant_id={tid}&skip=0&limit=50", headers=h).json()
sup_ids = [s["id"] for s in sups.get("items", sups)]

emps = c.get(f"{B}/mgmt/hr/employees", headers=h).json()
emp_ids = [e["id"] for e in (emps if isinstance(emps, list) else emps.get("items", []))]

wos = c.get(f"{B}/mfg/work-orders", headers=h).json()
wo_items = wos.get("items", wos) if isinstance(wos, dict) else wos
wo_ids = [w["id"] for w in wo_items[:50]]

# 1. Service Tickets (30)
print("=== 1. 售后工单 (30条) ===")
descs = ["产品外观划伤","功能异常需更换","物流运输损坏","安装指导需求","配件缺失","性能不达标","噪音异常","接口松动"]
for i in range(30):
    if not cust_ids: break
    post("/plm/service/tickets", {
        "customer_id": random.choice(cust_ids),
        "ticket_no": f"SVC-{uuid4().hex[:6]}",
        "description": random.choice(descs),
    })
print(f"  {ok} ok, {fail} fail"); ok=fail=0

# 2. Job Tickets (50)
print("\n=== 2. 工序报工 (50条) ===")
for i in range(50):
    if not wo_ids: break
    post("/mfg/job-tickets", {
        "work_order_id": random.choice(wo_ids),
        "ticket_no": f"JT-{uuid4().hex[:6]}",
    })
print(f"  {ok} ok, {fail} fail"); ok=fail=0

# 3. Purchase Orders (30)
print("\n=== 3. 采购单 (30条) ===")
for i in range(30):
    if not sup_ids or not prod_ids: break
    qty = random.choice([50,100,200,500])
    price = round(random.uniform(10, 200), 2)
    post("/scm/purchase-orders", {
        "order_no": f"PO-{uuid4().hex[:6]}",
        "supplier_id": random.choice(sup_ids),
        "lines": [{"product_id": random.choice(prod_ids), "quantity": qty, "uom": "pcs", "unit_price": price}],
    }, params={"tenant_id": tid})
print(f"  {ok} ok, {fail} fail"); ok=fail=0

# Verify all
print("\n=== 验证 ===")
for name, path in [
    ("售后工单", "/plm/service/tickets"),
    ("工序报工", "/mfg/job-tickets"),
    ("采购单", f"/scm/purchase-orders?tenant_id={tid}"),
]:
    r = c.get(f"{B}{path}", headers=h)
    if r.status_code >= 400:
        print(f"  {name}: ERROR {r.status_code}")
    else:
        d = r.json()
        items = d if isinstance(d, list) else d.get("items", [])
        print(f"  {name}: {len(items)} 条")

print("\n完成!")
