#!/usr/bin/env python3
"""注入库存数据: 采购入库 → 库存产生 → 盘点"""
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
tp = {"tenant_id": tid}

ok = fail = 0
def post(path, data, params=None, label=""):
    global ok, fail
    r = c.post(f"{B}{path}", headers=h, json=data, params=params)
    if r.status_code < 400:
        ok += 1
        return r.json()
    fail += 1
    detail = ""
    try:
        d = r.json()
        detail = d.get("detail", "")
        if isinstance(detail, list):
            detail = "; ".join(x.get("msg", "") for x in detail[:3])
    except:
        detail = r.text[:100]
    print(f"    FAIL [{r.status_code}] {label}: {detail}")
    return None

# Load existing IDs
prods = c.get(f"{B}/plm/products?skip=0&limit=50", headers=h).json()
prod_ids = [p["id"] for p in prods.get("items", prods)]

sups = c.get(f"{B}/scm/suppliers?tenant_id={tid}&skip=0&limit=50", headers=h).json()
sup_ids = [s["id"] for s in sups.get("items", sups)]

whs = c.get(f"{B}/scm/warehouses?tenant_id={tid}&skip=0&limit=50", headers=h).json()
wh_items = whs.get("items", whs) if isinstance(whs, dict) else whs
wh_ids = [w["id"] for w in wh_items]

pos_r = c.get(f"{B}/scm/purchase-orders?tenant_id={tid}", headers=h).json()
po_list = pos_r if isinstance(pos_r, list) else (pos_r.get("items", []) if isinstance(pos_r, dict) else [])

wos = c.get(f"{B}/mfg/work-orders", headers=h).json()
wo_items = wos.get("items", wos) if isinstance(wos, dict) else wos
wo_ids = [w["id"] for w in (wo_items if isinstance(wo_items, list) else [])[:30]]

print(f"已有数据: {len(prod_ids)} 产品, {len(sup_ids)} 供应商, {len(wh_ids)} 仓库, {len(po_list)} 采购单, {len(wo_ids)} 工单")

# ═══════════════════════════════════════════════════════════════
# Phase 0: 审批采购单 (draft → submitted → approved)
# ═══════════════════════════════════════════════════════════════
print("\n═══ Phase 0: 审批采购单 ═══")
approved_po_ids = []
for po in po_list[:30]:
    po_id = po["id"]
    status = po.get("status", "draft")
    # Push through: draft → submitted → approved
    if status == "draft":
        r = c.post(f"{B}/scm/purchase-orders/{po_id}/transition", headers=h, json={"to_status": "submitted"}, params=tp)
        if r.status_code < 400:
            status = "submitted"
    if status == "submitted":
        r = c.post(f"{B}/scm/purchase-orders/{po_id}/transition", headers=h, json={"to_status": "approved"}, params=tp)
        if r.status_code < 400:
            status = "approved"
    if status == "approved":
        approved_po_ids.append(po_id)
print(f"  已审批 {len(approved_po_ids)} 张采购单")

# ═══════════════════════════════════════════════════════════════
# Phase 1: 采购收货入库 (30笔) → 产生库存
# ═══════════════════════════════════════════════════════════════
print("\n═══ Phase 1: 采购收货入库 (30笔) ═══")
batches_created = []  # (product_id, batch_no, wh_id, qty)

for i in range(30):
    pid = random.choice(prod_ids)
    sid = random.choice(sup_ids) if sup_ids else str(uuid4())
    wh_id = random.choice(wh_ids) if wh_ids else None
    qty = random.choice([50, 100, 200, 500, 1000])
    batch_no = f"B{datetime.now().strftime('%y%m')}-{uuid4().hex[:4]}"

    # 用已审批的 PO
    if not approved_po_ids:
        print("    无已审批采购单, 跳过")
        break
    po_id = approved_po_ids[i % len(approved_po_ids)]

    receipt = post("/scm/purchase-receipts", {
        "receipt_no": f"RCV-{uuid4().hex[:6]}",
        "order_id": po_id,
        "supplier_id": sid,
        "warehouse_id": wh_id,
        "received_at": (datetime.now() - timedelta(days=random.randint(1, 300))).isoformat(),
        "lines": [{
            "product_id": pid,
            "ordered_quantity": qty,
            "received_quantity": qty - random.randint(0, int(qty * 0.05)),  # 98-100% 到货
            "rejected_quantity": random.randint(0, 3),
            "uom": "pcs",
            "batch_no": batch_no,
        }],
    }, params=tp, label=f"入库#{i+1}")

    if receipt:
        actual_qty = qty - random.randint(0, int(qty * 0.05))
        batches_created.append((pid, batch_no, wh_id, actual_qty))

print(f"  入库: {ok} ok, {fail} fail")
ok_save = ok; fail_save = fail; ok = fail = 0

# ═══════════════════════════════════════════════════════════════
# Phase 2: 生产领料 (20笔) → 减少库存
# ═══════════════════════════════════════════════════════════════
print("\n═══ Phase 2: 生产领料 (20笔) ═══")
for i in range(20):
    if not batches_created or not wo_ids:
        break
    pid, batch, wh_id, available = random.choice(batches_created)
    issue_qty = min(random.randint(10, 50), available)

    post("/scm/issue", {
        "product_id": pid,
        "quantity": issue_qty,
        "uom": "pcs",
        "warehouse_id": wh_id,
        "batch_no": batch,
        "work_order_id": random.choice(wo_ids),
    }, params=tp, label=f"领料#{i+1}")

print(f"  领料: {ok} ok, {fail} fail")
ok_save += ok; fail_save += fail; ok = fail = 0

# ═══════════════════════════════════════════════════════════════
# Phase 3: 仓库盘点 (每个仓库1次) → 盘点记录
# ═══════════════════════════════════════════════════════════════
print("\n═══ Phase 3: 仓库盘点 ═══")
for wh in wh_items[:4] if isinstance(wh_items, list) else []:
    wh_id = wh["id"]
    wh_name = wh.get("name", wh.get("code", "?"))

    # 选 3-5 个产品盘点
    sampled = random.sample(prod_ids, min(5, len(prod_ids)))
    lines = []
    for pid in sampled:
        lines.append({
            "product_id": pid,
            "batch_no": f"B{random.randint(2501,2603):04d}-{uuid4().hex[:4]}",
            "uom": "pcs",
            "actual_quantity": random.randint(10, 500),
        })

    st = post("/scm/stocktakes", {
        "stocktake_no": f"ST-{uuid4().hex[:6]}",
        "warehouse_id": wh_id,
        "stocktake_date": datetime.now().isoformat(),
        "remark": f"{wh_name}月度盘点",
        "lines": lines,
    }, params=tp, label=f"盘点-{wh_name}")

print(f"  盘点: {ok} ok, {fail} fail")
ok_save += ok; fail_save += fail; ok = fail = 0

# ═══════════════════════════════════════════════════════════════
# Verify
# ═══════════════════════════════════════════════════════════════
print("\n═══ 验证 ═══")
for name, path in [
    ("库存", f"/scm/inventory?tenant_id={tid}"),
    ("盘点", f"/scm/stocktakes?tenant_id={tid}"),
]:
    r = c.get(f"{B}{path}", headers=h)
    d = r.json()
    items = d if isinstance(d, list) else d.get("items", [])
    print(f"  {name}: {len(items)} 条")

print(f"\n总计: {ok_save} ok, {fail_save} fail")
