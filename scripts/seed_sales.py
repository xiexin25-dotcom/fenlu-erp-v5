#!/usr/bin/env python3
"""Seed 20 sales orders with various payment/shipment states."""
import random
from datetime import date, timedelta
from uuid import uuid4
import httpx

B = "http://localhost:8000"
c = httpx.Client(timeout=30)
r = c.post(f"{B}/auth/login", json={"tenant_code": "demo", "username": "admin", "password": "admin123"})
h = {"Authorization": f"Bearer {r.json()['access_token']}", "Content-Type": "application/json"}

custs = c.get(f"{B}/plm/customers", headers=h).json()
prods = c.get(f"{B}/plm/products?skip=0&limit=20", headers=h).json().get("items", [])

ok = 0
for i in range(20):
    cust = random.choice(custs)
    prod = random.choice(prods)
    qty = random.choice([50, 100, 200, 500])
    price = round(random.uniform(50, 500), 2)
    d = date.today() - timedelta(days=random.randint(0, 90))
    r = c.post(f"{B}/sales", headers=h, json={
        "order_no": f"SO-{d.strftime('%m%d')}-{uuid4().hex[:4]}",
        "customer_id": cust["id"], "customer_name": cust["name"],
        "order_date": d.isoformat(),
        "delivery_date": (d + timedelta(days=random.randint(7, 30))).isoformat(),
        "salesperson": random.choice(["刘洋", "张伟", "李娜"]),
        "items": [{"product_id": prod["id"], "product_name": prod.get("name", ""), "quantity": qty, "unit_price": price}],
    })
    if r.status_code < 400:
        ok += 1
        oid = r.json()["id"]
        if random.random() < 0.8:
            c.post(f"{B}/sales/{oid}/confirm", headers=h)
        if random.random() < 0.4:
            c.post(f"{B}/sales/{oid}/payment", headers=h, json={"amount": float(qty * price)})
        if random.random() < 0.3:
            c.post(f"{B}/sales/{oid}/ship", headers=h)

print(f"创建 {ok} 个销售订单")
stats = c.get(f"{B}/sales/stats/summary", headers=h).json()
print(f"统计: {stats}")
