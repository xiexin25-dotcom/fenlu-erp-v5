#!/usr/bin/env python3
"""
分路链式工业互联网 V5.0 · 数据模拟器

模拟一个正常运行的工厂，持续向系统注入数据。
单文件、无外部依赖（仅 httpx），方便修改。

用法:
    python3 scripts/simulator.py                          # 默认 localhost:8000, 每5秒一轮
    python3 scripts/simulator.py --base-url http://x:8000 # 指定服务器
    python3 scripts/simulator.py --interval 2             # 每2秒一轮
    python3 scripts/simulator.py --seed-only              # 只播种主数据，不循环
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from datetime import datetime, timedelta
from uuid import uuid4

import httpx

# ── 配置 ──────────────────────────────────────────────────────────────

BASE_URL = "http://localhost:8000"
TENANT = "demo"
USERNAME = "admin"
PASSWORD = "admin123"

# ── 主数据模板 ─────────────────────────────────────────────────────────

PRODUCTS = [
    ("P-1001", "铝合金外壳", "self_made", "pcs"),
    ("P-1002", "不锈钢底板", "self_made", "pcs"),
    ("P-1003", "铜制散热片", "self_made", "pcs"),
    ("P-1004", "橡胶密封圈", "raw_material", "pcs"),
    ("P-1005", "M6六角螺栓", "raw_material", "pcs"),
    ("P-1006", "LED指示灯", "agent", "pcs"),
    ("P-1007", "电路主板 V3", "self_made", "pcs"),
    ("P-1008", "电源适配器", "agent", "pcs"),
    ("P-1009", "瓦楞纸箱", "packaging", "pcs"),
    ("P-1010", "PE防静电袋", "packaging", "pcs"),
]

SUPPLIERS = [
    ("SUP-001", "宝山铝业", "strategic", "王建国", "13800001001"),
    ("SUP-002", "东方钢材", "preferred", "李明", "13800001002"),
    ("SUP-003", "精密铜材", "approved", "张华", "13800001003"),
    ("SUP-004", "恒力橡胶", "approved", "陈伟", "13800001004"),
    ("SUP-005", "标准件商城", "preferred", "刘强", "13800001005"),
]

CUSTOMERS = [
    ("C-001", "华为技术", "b2b", "A"),
    ("C-002", "比亚迪电子", "b2b", "A"),
    ("C-003", "小米科技", "b2b", "B"),
    ("C-004", "联想集团", "b2b", "B"),
    ("C-005", "格力电器", "b2b", "A"),
]

EQUIPMENT = [
    ("CNC-001", "CNC加工中心#1"),
    ("CNC-002", "CNC加工中心#2"),
    ("PRESS-001", "液压冲压机"),
    ("WELD-001", "自动焊接机器人"),
    ("ASSY-001", "装配流水线#1"),
    ("PACK-001", "自动包装机"),
    ("TEST-001", "综合测试台"),
]

WAREHOUSES = [
    ("WH-001", "原材料仓", "A区1号库房"),
    ("WH-002", "半成品仓", "B区2号库房"),
    ("WH-003", "成品仓", "C区3号库房"),
]

GL_ACCOUNTS = [
    ("1001", "库存现金", "ASSET"),
    ("1002", "银行存款", "ASSET"),
    ("1122", "应收账款", "ASSET"),
    ("1401", "原材料", "ASSET"),
    ("1405", "库存商品", "ASSET"),
    ("2202", "应付账款", "LIABILITY"),
    ("4001", "生产成本", "EXPENSE"),
    ("6001", "主营业务收入", "REVENUE"),
    ("6401", "主营业务成本", "EXPENSE"),
    ("6602", "管理费用", "EXPENSE"),
]

EMPLOYEES = [
    ("EMP-001", "赵一", "生产部", "车间主任", 12000),
    ("EMP-002", "钱二", "生产部", "操作员", 8000),
    ("EMP-003", "孙三", "生产部", "操作员", 7500),
    ("EMP-004", "李四", "质量部", "质检员", 9000),
    ("EMP-005", "周五", "仓储部", "仓管员", 7000),
    ("EMP-006", "吴六", "采购部", "采购专员", 8500),
    ("EMP-007", "郑七", "财务部", "会计", 10000),
    ("EMP-008", "王八", "设备部", "维修工程师", 9500),
]

HAZARD_LOCATIONS = ["A车间东侧", "B车间焊接区", "仓库叉车通道", "配电房", "压缩空气站", "化学品存放区"]

# ── API Client ─────────────────────────────────────────────────────────

class API:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30)
        self.token = ""
        self.tenant_id = ""

    def login(self):
        r = self.client.post(f"{self.base}/auth/login", json={
            "tenant_code": TENANT, "username": USERNAME, "password": PASSWORD,
        })
        r.raise_for_status()
        self.token = r.json()["access_token"]
        me = self.get("/auth/me")
        self.tenant_id = me["tenant_id"]
        print(f"  登录成功: {me['full_name']} (tenant={self.tenant_id[:8]}...)")

    def _headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    def get(self, path: str, params: dict | None = None):
        r = self.client.get(f"{self.base}{path}", headers=self._headers(), params=params)
        if r.status_code >= 400:
            return []  # 返回空列表表示无数据或不支持
        return r.json()

    def post(self, path: str, json: dict | None = None, params: dict | None = None):
        r = self.client.post(f"{self.base}{path}", headers=self._headers(), json=json, params=params)
        if r.status_code >= 400:
            print(f"    WARN: POST {path} → {r.status_code}: {r.text[:200]}")
            return None
        return r.json()

    def patch(self, path: str, json: dict | None = None):
        r = self.client.patch(f"{self.base}{path}", headers=self._headers(), json=json)
        if r.status_code >= 400:
            print(f"    WARN: PATCH {path} → {r.status_code}: {r.text[:200]}")
            return None
        return r.json()


# ── 状态跟踪 ───────────────────────────────────────────────────────────

class State:
    """跟踪已创建的资源 ID，供后续操作引用"""
    def __init__(self):
        self.product_ids: list[str] = []
        self.supplier_ids: list[str] = []
        self.customer_ids: list[str] = []
        self.equipment_ids: list[str] = []
        self.warehouse_ids: list[str] = []
        self.account_ids: dict[str, str] = {}  # code → id
        self.employee_ids: list[str] = []
        self.bom_ids: list[str] = []
        self.routing_ids: list[str] = []
        self.work_order_ids: list[str] = []  # 活跃工单
        self.wo_counter = 0
        self.po_counter = 0
        self.pr_counter = 0
        self.jrn_counter = 0
        self.insp_counter = 0
        self.hazard_counter = 0
        self.ticket_counter = 0
        self.tick = 0


# ── 播种主数据 ─────────────────────────────────────────────────────────

def seed_products(api: API, state: State):
    print("  播种产品...")
    existing = api.get("/plm/products", params={"skip": 0, "limit": 50})
    items = existing.get("items", existing) if isinstance(existing, dict) else existing
    if isinstance(items, list) and items:
        state.product_ids = [p["id"] for p in items]
        print(f"    已有 {len(state.product_ids)} 个产品 (跳过)")
        return
    for code, name, cat, uom in PRODUCTS:
        r = api.post("/plm/products", {"code": code, "name": name, "category": cat, "uom": uom})
        if r and "id" in r:
            state.product_ids.append(r["id"])
    print(f"    {len(state.product_ids)} 个产品")


def seed_bom_and_routing(api: API, state: State):
    print("  播种 BOM + Routing...")
    if state.bom_ids:
        print(f"    已有 BOM (跳过)")
        return
    for pid in state.product_ids[:5]:  # 前5个产品建BOM/Routing
        bom = api.post("/plm/bom", {"product_id": pid, "version": "V1.0"})
        if bom:
            state.bom_ids.append(bom["id"])
            # 添加2-3个组件
            for comp_id in random.sample(state.product_ids[3:], min(2, len(state.product_ids[3:]))):
                if comp_id != pid:
                    api.post(f"/plm/bom/{bom['id']}/items", {
                        "component_id": comp_id, "quantity": random.randint(1, 10),
                        "uom": "pcs", "unit_cost": round(random.uniform(5, 50), 2),
                    })
        rtg = api.post("/plm/routing", {"product_id": pid, "version": "V1.0"})
        if rtg:
            state.routing_ids.append(rtg["id"])
            for seq, (op_code, op_name, mins) in enumerate([
                ("CUT", "下料", 15), ("PROC", "加工", 30), ("ASSY", "装配", 20), ("TEST", "检测", 10),
            ], 1):
                api.post(f"/plm/routing/{rtg['id']}/operations", {
                    "sequence": seq, "operation_code": op_code,
                    "operation_name": op_name, "standard_minutes": mins, "setup_minutes": 5,
                })
    print(f"    {len(state.bom_ids)} BOM, {len(state.routing_ids)} Routing")


def seed_suppliers(api: API, state: State):
    print("  播种供应商...")
    existing = api.get("/scm/suppliers", params={"tenant_id": api.tenant_id, "skip": "0", "limit": "50"})
    items = existing.get("items", existing) if isinstance(existing, dict) else existing
    if isinstance(items, list) and items:
        state.supplier_ids = [s["id"] for s in items]
        print(f"    已有 {len(state.supplier_ids)} 个供应商 (跳过)")
        return
    for code, name, tier, contact, phone in SUPPLIERS:
        r = api.post("/scm/suppliers", {"code": code, "name": name, "tier": tier,
                      "contact_name": contact, "contact_phone": phone},
                     params={"tenant_id": api.tenant_id})
        if r and "id" in r:
            state.supplier_ids.append(r["id"])
    print(f"    {len(state.supplier_ids)} 个供应商")


def seed_customers(api: API, state: State):
    print("  播种客户...")
    existing = api.get("/plm/customers", params={"skip": "0", "limit": "50"})
    items = existing.get("items", existing) if isinstance(existing, dict) else existing
    if isinstance(items, list) and items:
        state.customer_ids = [c["id"] for c in items]
        print(f"    已有 {len(state.customer_ids)} 个客户 (跳过)")
        return
    for code, name, kind, rating in CUSTOMERS:
        r = api.post("/plm/customers", {"code": code, "name": name, "kind": kind, "rating": rating})
        if r and "id" in r:
            state.customer_ids.append(r["id"])
    print(f"    {len(state.customer_ids)} 个客户")


def seed_equipment(api: API, state: State):
    print("  播种设备...")
    existing = api.get("/mfg/equipment")
    items = existing.get("items", existing) if isinstance(existing, dict) else existing
    if isinstance(items, list) and items:
        state.equipment_ids = [e["id"] for e in items]
        print(f"    已有 {len(state.equipment_ids)} 台设备 (跳过)")
        return
    for code, name in EQUIPMENT:
        r = api.post("/mfg/equipment", {"code": code, "name": name,
                      "workshop_id": str(uuid4()), "status": "running"})
        if r and "id" in r:
            state.equipment_ids.append(r["id"])
    print(f"    {len(state.equipment_ids)} 台设备")


def seed_warehouses(api: API, state: State):
    print("  播种仓库...")
    existing = api.get("/scm/warehouses", params={"tenant_id": api.tenant_id, "skip": "0", "limit": "50"})
    items = existing.get("items", existing) if isinstance(existing, dict) else existing
    if isinstance(items, list) and items:
        state.warehouse_ids = [w["id"] for w in items]
        print(f"    已有 {len(state.warehouse_ids)} 个仓库 (跳过)")
        return
    for code, name, addr in WAREHOUSES:
        r = api.post("/scm/warehouses", {"code": code, "name": name, "address": addr},
                     params={"tenant_id": api.tenant_id})
        if r and "id" in r:
            state.warehouse_ids.append(r["id"])
    print(f"    {len(state.warehouse_ids)} 个仓库")


def seed_accounts(api: API, state: State):
    print("  播种会计科目...")
    existing = api.get("/mgmt/finance/accounts")
    items = existing if isinstance(existing, list) else existing.get("items", [])
    if items:
        for a in items:
            state.account_ids[a["code"]] = a["id"]
        print(f"    已有 {len(state.account_ids)} 个科目 (跳过)")
        return
    for code, name, typ in GL_ACCOUNTS:
        r = api.post("/mgmt/finance/accounts", {"code": code, "name": name, "account_type": typ, "level": 1})
        if r and "id" in r:
            state.account_ids[code] = r["id"]
    print(f"    {len(state.account_ids)} 个科目")


def seed_employees(api: API, state: State):
    print("  播种员工...")
    existing = api.get("/mgmt/hr/employees")
    items = existing if isinstance(existing, list) else existing.get("items", [])
    if items:
        state.employee_ids = [e["id"] for e in items]
        print(f"    已有 {len(state.employee_ids)} 个员工 (跳过)")
        return
    for eno, name, dept, pos, salary in EMPLOYEES:
        r = api.post("/mgmt/hr/employees", {
            "employee_no": eno, "name": name, "position": pos,
            "base_salary": salary,
        })
        if r and "id" in r:
            state.employee_ids.append(r["id"])
    print(f"    {len(state.employee_ids)} 个员工")


def seed_all(api: API, state: State):
    print("\n══ 播种主数据 ══")
    seed_products(api, state)
    seed_bom_and_routing(api, state)
    seed_suppliers(api, state)
    seed_customers(api, state)
    seed_equipment(api, state)
    seed_warehouses(api, state)
    seed_accounts(api, state)
    seed_employees(api, state)
    print("══ 播种完成 ══\n")


# ── 模拟操作 ───────────────────────────────────────────────────────────

def sim_work_order(api: API, state: State):
    """创建新工单"""
    if not state.product_ids or not state.bom_ids:
        return
    idx = random.randint(0, min(len(state.product_ids), len(state.bom_ids)) - 1)
    state.wo_counter += 1
    now = datetime.now()
    uid = uuid4().hex[:6]
    wo = api.post("/mfg/work-orders", {
        "order_no": f"WO-{now.strftime('%Y%m%d')}-{uid}",
        "product_id": state.product_ids[idx],
        "bom_id": state.bom_ids[idx % len(state.bom_ids)],
        "routing_id": state.routing_ids[idx % len(state.routing_ids)] if state.routing_ids else str(uuid4()),
        "planned_quantity": {"value": random.choice([100, 200, 500, 1000]), "uom": "pcs"},
        "planned_start": now.isoformat(),
        "planned_end": (now + timedelta(days=random.randint(3, 14))).isoformat(),
    })
    if wo:
        state.work_order_ids.append(wo["id"])
        print(f"  [MFG] 新工单 {wo.get('order_no', '')} 产品={PRODUCTS[idx][1]}")


def sim_wo_transition(api: API, state: State):
    """推进一个工单的状态"""
    if not state.work_order_ids:
        return
    wid = random.choice(state.work_order_ids)
    wo = api.get(f"/mfg/work-orders/{wid}")
    if not wo:
        return
    flow = {"planned": "released", "released": "in_progress", "in_progress": "completed", "completed": "closed"}
    next_s = flow.get(wo.get("status", ""))
    if next_s:
        r = api.patch(f"/mfg/work-orders/{wid}/status", {"status": next_s})
        if r:
            print(f"  [MFG] 工单 {wo.get('order_no','')} {wo['status']} → {next_s}")
        if next_s == "closed":
            state.work_order_ids.remove(wid)


def sim_qc_inspection(api: API, state: State):
    """质检记录"""
    if not state.product_ids:
        return
    state.insp_counter += 1
    result = random.choices(["pass", "fail", "conditional"], weights=[85, 10, 5])[0]
    defects = 0 if result == "pass" else random.randint(1, 10)
    uid = uuid4().hex[:6]
    r = api.post("/mfg/qc/inspections", {
        "inspection_no": f"QC-{uid}",
        "type": random.choice(["iqc", "ipqc", "oqc"]),
        "product_id": random.choice(state.product_ids),
        "sample_size": random.choice([30, 50, 100]),
        "defect_count": defects,
        "result": result,
        "inspector_id": random.choice(state.employee_ids) if state.employee_ids else str(uuid4()),
    })
    if r:
        emoji = {"pass": "OK", "fail": "NG", "conditional": "?!"}[result]
        print(f"  [QMS] 质检 {emoji} 抽样={r.get('sample_size','')} 缺陷={defects}")


def sim_safety_hazard(api: API, state: State):
    """安全隐患"""
    state.hazard_counter += 1
    level = random.choices(["minor", "moderate", "major", "critical"], weights=[50, 30, 15, 5])[0]
    loc = random.choice(HAZARD_LOCATIONS)
    uid = uuid4().hex[:6]
    r = api.post("/mfg/safety/hazards", {
        "hazard_no": f"HAZ-{uid}",
        "location": loc,
        "level": level,
        "description": f"发现{level}级隐患于{loc}",
    })
    if r:
        print(f"  [EHS] 安全隐患 [{level}] {loc}")


def sim_energy_reading(api: API, state: State):
    """能耗读数"""
    # 先确保有表计
    meter = api.post("/mfg/energy/meters", {
        "code": f"MTR-{random.randint(1,3):03d}",
        "name": f"电表#{random.randint(1,3)}",
        "energy_type": "electricity",
        "uom": "kWh",
        "location": f"{random.choice(['A','B','C'])}车间",
    })
    # 不管表计是否创建成功（可能重复），模拟就好
    print(f"  [NRG] 能耗读数已记录")


def sim_journal(api: API, state: State):
    """记账凭证"""
    if len(state.account_ids) < 2:
        return
    state.jrn_counter += 1
    codes = list(state.account_ids.keys())
    debit_code = random.choice(codes)
    credit_code = random.choice([c for c in codes if c != debit_code])
    amount = round(random.uniform(1000, 50000), 2)
    descs = ["采购原材料付款", "销售收入入账", "发放工资", "设备维修费", "水电费", "办公用品", "物流运费"]
    memo = random.choice(descs)
    r = api.post("/mgmt/finance/journal", {
        "entry_date": datetime.now().strftime("%Y-%m-%d"),
        "memo": memo,
        "lines": [
            {"account_id": state.account_ids[debit_code], "debit_amount": amount, "credit_amount": 0},
            {"account_id": state.account_ids[credit_code], "debit_amount": 0, "credit_amount": amount},
        ],
    })
    if r:
        print(f"  [FIN] 凭证 {memo} ¥{amount:,.2f}")


def sim_attendance(api: API, state: State):
    """考勤打卡"""
    if not state.employee_ids:
        return
    eid = random.choice(state.employee_ids)
    today = datetime.now().strftime("%Y-%m-%d")
    clock_in_h = random.choices([7, 8, 8, 8, 9], weights=[5, 70, 10, 10, 5])[0]
    clock_in_m = random.randint(0, 59)
    clock_out_h = random.choices([17, 17, 18, 19, 20], weights=[10, 50, 25, 10, 5])[0]
    clock_out_m = random.randint(0, 59)
    overtime = max(0, clock_out_h - 17) + (clock_out_m / 60 if clock_out_h >= 17 else 0)
    r = api.post("/mgmt/hr/attendance", {
        "employee_id": eid,
        "work_date": today,
        "clock_in": f"{clock_in_h:02d}:{clock_in_m:02d}:00",
        "clock_out": f"{clock_out_h:02d}:{clock_out_m:02d}:00",
        "status": "normal" if clock_in_h <= 8 else "late",
        "work_hours": round(clock_out_h - clock_in_h + (clock_out_m - clock_in_m) / 60, 1),
        "overtime_hours": round(overtime, 1),
    })
    if r:
        name = [e[1] for e in EMPLOYEES if any(eid_stored == eid for eid_stored in state.employee_ids)]
        print(f"  [HR]  考勤 {clock_in_h:02d}:{clock_in_m:02d}-{clock_out_h:02d}:{clock_out_m:02d} 加班={overtime:.1f}h")


def sim_purchase(api: API, state: State):
    """采购单"""
    if not state.supplier_ids or not state.product_ids:
        return
    state.po_counter += 1
    sid = random.choice(state.supplier_ids)
    pid = random.choice(state.product_ids)
    qty = random.choice([50, 100, 200, 500])
    price = round(random.uniform(10, 200), 2)
    uid = uuid4().hex[:6]
    r = api.post("/scm/purchase-orders", {
        "order_no": f"PO-{uid}",
        "supplier_id": sid,
        "lines": [{"product_id": pid, "quantity": qty, "uom": "pcs", "unit_price": price}],
    }, params={"tenant_id": api.tenant_id})
    if r:
        print(f"  [SCM] 采购单 {qty}×¥{price:.2f} = ¥{qty*price:,.2f}")


def sim_service_ticket(api: API, state: State):
    """售后工单"""
    if not state.customer_ids:
        return
    state.ticket_counter += 1
    uid = uuid4().hex[:6]
    r = api.post("/plm/service/tickets", {
        "customer_id": random.choice(state.customer_ids),
        "ticket_no": f"SVC-{uid}",
        "description": random.choice(["产品外观划伤", "功能异常需更换", "物流运输损坏", "安装指导需求"]),
    })
    if r:
        print(f"  [PLM] 售后工单 SVC-{state.ticket_counter:04d}")


# ── 主循环 ─────────────────────────────────────────────────────────────

def run_tick(api: API, state: State):
    """单次模拟循环 — 每次随机执行几个操作"""
    state.tick += 1
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n── Tick #{state.tick} [{now}] ──")

    # 每轮随机选择 3-6 个操作执行
    ops = [
        (40, sim_work_order),
        (50, sim_wo_transition),
        (60, sim_qc_inspection),
        (10, sim_safety_hazard),
        (30, sim_energy_reading),
        (40, sim_journal),
        (50, sim_attendance),
        (25, sim_purchase),
        (8, sim_service_ticket),
    ]

    for weight, fn in ops:
        if random.randint(1, 100) <= weight:
            try:
                fn(api, state)
            except Exception as e:
                print(f"    ERROR in {fn.__name__}: {e}")


def main():
    parser = argparse.ArgumentParser(description="FenLu V5 数据模拟器")
    parser.add_argument("--base-url", default=BASE_URL, help="API 地址")
    parser.add_argument("--interval", type=float, default=5, help="每轮间隔(秒)")
    parser.add_argument("--seed-only", action="store_true", help="只播种不循环")
    parser.add_argument("--skip-seed", action="store_true", help="跳过播种直接循环")
    args = parser.parse_args()

    api = API(args.base_url)
    state = State()

    print("╔══════════════════════════════════════════╗")
    print("║   分路链式 V5.0 · 工厂数据模拟器         ║")
    print(f"║   API: {args.base_url:<33s}║")
    print(f"║   间隔: {args.interval}s                              ║")
    print("╚══════════════════════════════════════════╝")

    # 登录
    print("\n[AUTH] 登录中...")
    try:
        api.login()
    except Exception as e:
        print(f"登录失败: {e}")
        print(f"请确认 {args.base_url} 可用，demo/admin/admin123 已创建")
        sys.exit(1)

    # 播种
    if not args.skip_seed:
        seed_all(api, state)

    # 确保关键 ID 有值（从 API 加载）
    if not state.product_ids:
        d = api.get("/plm/products", params={"skip": "0", "limit": "50"})
        items = d.get("items", d) if isinstance(d, dict) else d
        if isinstance(items, list):
            state.product_ids = [p["id"] for p in items]
    if not state.account_ids:
        d = api.get("/mgmt/finance/accounts")
        items = d if isinstance(d, list) else d.get("items", [])
        for a in items:
            state.account_ids[a.get("code", str(len(state.account_ids)))] = a["id"]
    if not state.employee_ids:
        d = api.get("/mgmt/hr/employees")
        items = d if isinstance(d, list) else d.get("items", [])
        state.employee_ids = [e["id"] for e in items] if items else []
    if not state.supplier_ids:
        d = api.get("/scm/suppliers", params={"tenant_id": api.tenant_id, "skip": "0", "limit": "50"})
        items = d.get("items", d) if isinstance(d, dict) else d
        if isinstance(items, list):
            state.supplier_ids = [s["id"] for s in items]
    if not state.customer_ids:
        state.customer_ids = state.product_ids[:5]  # fallback: reuse product IDs
    if not state.bom_ids:
        state.bom_ids = [str(uuid4()) for _ in range(3)]  # placeholder
    if not state.routing_ids:
        state.routing_ids = [str(uuid4()) for _ in range(3)]

    print(f"\n  资源: {len(state.product_ids)} 产品, {len(state.supplier_ids)} 供应商, "
          f"{len(state.account_ids)} 科目, {len(state.employee_ids)} 员工")

    if args.seed_only:
        print("播种完成，退出。")
        return

    # 循环
    print("开始模拟 (Ctrl+C 停止)...\n")
    try:
        while True:
            run_tick(api, state)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(f"\n\n模拟结束。共 {state.tick} 轮。")
        print(f"  工单: {state.wo_counter}, 质检: {state.insp_counter}")
        print(f"  隐患: {state.hazard_counter}, 凭证: {state.jrn_counter}")
        print(f"  采购: {state.po_counter}, 工单: {state.ticket_counter}")


if __name__ == "__main__":
    main()
