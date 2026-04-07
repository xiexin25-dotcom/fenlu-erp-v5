#!/usr/bin/env python3
"""
分路链式 V5.0 · 100人工厂全场景初始化 + 运营模拟

模拟一家拥有100名员工的制造企业从零开始：
  Phase 1: 组织架构 (部门、员工)
  Phase 2: 产品体系 (产品、BOM、工艺路线)
  Phase 3: 供应链 (供应商、仓库、库位)
  Phase 4: 财务体系 (科目、期初余额)
  Phase 5: 客户体系 (客户、联系人)
  Phase 6: 设备与能源 (设备、能源表计)
  Phase 7: 审批流程定义
  Phase 8: 运营模拟 (工单、采购、质检、考勤、凭证...)

用法:
    uv run python scripts/factory_bootstrap.py
    uv run python scripts/factory_bootstrap.py --phase 8          # 只跑某个阶段
    uv run python scripts/factory_bootstrap.py --skip-to-ops      # 跳过初始化直接运营
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

# ── 工厂数据模板 ─────────────────────────────────────────────────────

DEPARTMENTS = [
    ("D01", "总经办", ["总经理", "副总经理", "总经理助理"]),
    ("D02", "生产部", ["生产总监", "车间主任", "班组长", "操作员", "操作员", "操作员", "操作员", "操作员",
                     "操作员", "操作员", "操作员", "操作员", "操作员", "操作员", "操作员", "操作员",
                     "操作员", "操作员", "操作员", "操作员", "操作员", "操作员", "操作员", "操作员",
                     "操作员", "操作员", "操作员", "操作员", "操作员", "操作员"]),
    ("D03", "质量部", ["质量经理", "质检员", "质检员", "质检员", "质检员", "质检员", "SPC工程师"]),
    ("D04", "设备部", ["设备经理", "维修工程师", "维修工程师", "维修工程师", "电气技师"]),
    ("D05", "仓储部", ["仓储经理", "仓管员", "仓管员", "仓管员", "叉车司机", "叉车司机"]),
    ("D06", "采购部", ["采购经理", "采购专员", "采购专员", "采购专员"]),
    ("D07", "财务部", ["财务经理", "会计", "会计", "出纳"]),
    ("D08", "人事行政部", ["HR经理", "HR专员", "行政专员", "前台"]),
    ("D09", "销售部", ["销售总监", "销售经理", "销售代表", "销售代表", "销售代表", "销售代表",
                     "销售代表", "客服专员", "客服专员"]),
    ("D10", "技术研发部", ["研发总监", "产品工程师", "产品工程师", "工艺工程师", "工艺工程师",
                       "模具工程师", "测试工程师"]),
    ("D11", "安环部", ["安环经理", "安全专员", "环保专员"]),
]

SURNAMES = "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜戚谢邹喻柏窦章苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳丰鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮齐康"
GIVEN_NAMES = "伟芳娜敏静丽强磊洋勇艳杰娟涛明超秀霞平刚桂英华建文辉力民志永林玲红金素梅玉萍珍贞莉兰菊翠淑慧巧美婷"

PRODUCTS_DATA = [
    # (code, name, category, uom, ops)
    ("FP-001", "智能控制器总成", "self_made", "pcs", [("CUT","下料",10), ("SMT","贴片",25), ("WAVE","波峰焊",15), ("ASSY","装配",20), ("TEST","综测",15), ("PACK","包装",8)]),
    ("FP-002", "铝合金散热壳体", "self_made", "pcs", [("CUT","下料",8), ("CNC","精加工",35), ("ANOD","阳极氧化",20), ("INSP","检验",10)]),
    ("FP-003", "不锈钢底座", "self_made", "pcs", [("CUT","下料",6), ("STAMP","冲压",12), ("WELD","焊接",18), ("POLISH","抛光",15), ("INSP","检验",8)]),
    ("FP-004", "电源模块 48V/10A", "self_made", "pcs", [("SMT","贴片",20), ("REFLOW","回流焊",12), ("TEST","测试",25), ("CONFML","灌胶",15), ("PACK","包装",5)]),
    ("FP-005", "LED驱动板", "self_made", "pcs", [("SMT","贴片",18), ("WAVE","波峰焊",10), ("TEST","综测",20), ("PACK","包装",5)]),
    ("RM-001", "FR4覆铜板", "raw_material", "pcs", []),
    ("RM-002", "铝合金棒料 6063", "raw_material", "kg", []),
    ("RM-003", "304不锈钢板", "raw_material", "kg", []),
    ("RM-004", "电解电容 470uF/50V", "raw_material", "pcs", []),
    ("RM-005", "贴片电阻 0603", "raw_material", "pcs", []),
    ("RM-006", "MOS管 IRF540N", "raw_material", "pcs", []),
    ("RM-007", "变压器 EE42", "raw_material", "pcs", []),
    ("RM-008", "M4x12螺丝", "raw_material", "pcs", []),
    ("RM-009", "导热硅脂", "raw_material", "kg", []),
    ("RM-010", "瓦楞纸箱 40x30x20", "packaging", "pcs", []),
    ("RM-011", "PE泡棉衬垫", "packaging", "pcs", []),
    ("RM-012", "防静电袋 A4", "packaging", "pcs", []),
    ("AG-001", "连接器 DB25", "agent", "pcs", []),
    ("AG-002", "风扇 60x60", "agent", "pcs", []),
    ("AG-003", "LCD显示屏 3.5寸", "agent", "pcs", []),
]

SUPPLIERS_DATA = [
    ("SUP-001", "宝钢特钢", "strategic", "王建国", "13900001001", "上海市宝山区"),
    ("SUP-002", "南山铝业", "strategic", "李铝材", "13900001002", "山东省龙口市"),
    ("SUP-003", "深圳华强电子", "preferred", "张华强", "13900001003", "深圳市福田区华强北"),
    ("SUP-004", "东莞精密五金", "preferred", "陈精工", "13900001004", "东莞市长安镇"),
    ("SUP-005", "苏州纳米科技", "approved", "刘纳米", "13900001005", "苏州市工业园区"),
    ("SUP-006", "杭州包装材料", "approved", "周包装", "13900001006", "杭州市余杭区"),
    ("SUP-007", "温州标准件", "approved", "吴标准", "13900001007", "温州市永嘉县"),
    ("SUP-008", "台湾连展科技", "preferred", "林连展", "13900001008", "昆山市花桥镇"),
    ("SUP-009", "武汉光谷显示", "approved", "赵光谷", "13900001009", "武汉市东湖高新区"),
    ("SUP-010", "广州化工材料", "approved", "黄化工", "13900001010", "广州市黄埔区"),
]

CUSTOMERS_DATA = [
    ("CUST-001", "华为技术有限公司", "b2b", "A"), ("CUST-002", "比亚迪股份有限公司", "b2b", "A"),
    ("CUST-003", "小米科技有限公司", "b2b", "A"), ("CUST-004", "联想集团", "b2b", "B"),
    ("CUST-005", "格力电器", "b2b", "A"), ("CUST-006", "美的集团", "b2b", "B"),
    ("CUST-007", "海尔智家", "b2b", "B"), ("CUST-008", "TCL科技", "b2b", "B"),
    ("CUST-009", "京东方", "b2b", "A"), ("CUST-010", "中兴通讯", "b2b", "B"),
    ("CUST-011", "大疆创新", "b2b", "A"), ("CUST-012", "宁德时代", "b2b", "A"),
    ("CUST-013", "立讯精密", "b2b", "B"), ("CUST-014", "歌尔股份", "b2b", "B"),
    ("CUST-015", "汇川技术", "b2b", "A"),
]

EQUIPMENT_DATA = [
    ("CNC-001","CNC加工中心#1"),("CNC-002","CNC加工中心#2"),("CNC-003","CNC加工中心#3"),
    ("SMT-001","SMT贴片机#1"),("SMT-002","SMT贴片机#2"),
    ("REFLOW-001","回流焊炉"),("WAVE-001","波峰焊机"),
    ("PRESS-001","300T冲压机"),("PRESS-002","160T冲压机"),
    ("WELD-001","激光焊接机"),("WELD-002","机器人焊接站"),
    ("ANOD-001","阳极氧化线"),
    ("TEST-001","综合测试台#1"),("TEST-002","综合测试台#2"),("TEST-003","高压测试仪"),
    ("PACK-001","自动包装线"),
    ("CRANE-001","5T行车"),("FORKLIFT-001","3T叉车"),("FORKLIFT-002","2T叉车"),
    ("AIR-001","空压机30HP"),
]

WAREHOUSES_DATA = [
    ("WH-RM", "原材料仓", "A区1号库房"),
    ("WH-WIP", "半成品仓", "B区2号库房"),
    ("WH-FG", "成品仓", "C区3号库房"),
    ("WH-TOOL", "工具辅料仓", "D区4号库房"),
]

GL_ACCOUNTS_DATA = [
    ("1001","库存现金","ASSET"),("1002","银行存款","ASSET"),("1012","其他货币资金","ASSET"),
    ("1122","应收账款","ASSET"),("1123","预付账款","ASSET"),("1131","应收票据","ASSET"),
    ("1401","原材料","ASSET"),("1403","周转材料","ASSET"),("1405","库存商品","ASSET"),
    ("1411","在产品","ASSET"),("1501","固定资产","ASSET"),("1502","累计折旧","ASSET"),
    ("2001","短期借款","LIABILITY"),("2202","应付账款","LIABILITY"),("2203","预收账款","LIABILITY"),
    ("2211","应付职工薪酬","LIABILITY"),("2221","应交税费","LIABILITY"),("2241","其他应付款","LIABILITY"),
    ("3001","实收资本","EQUITY"),("3002","资本公积","EQUITY"),("3101","盈余公积","EQUITY"),
    ("3131","未分配利润","EQUITY"),
    ("6001","主营业务收入","REVENUE"),("6051","其他业务收入","REVENUE"),
    ("6301","营业外收入","REVENUE"),
    ("6401","主营业务成本","EXPENSE"),("6402","其他业务成本","EXPENSE"),
    ("6601","销售费用","EXPENSE"),("6602","管理费用","EXPENSE"),("6603","财务费用","EXPENSE"),
    ("6701","资产减值损失","EXPENSE"),("6711","营业外支出","EXPENSE"),
    ("6801","所得税费用","EXPENSE"),
]

HAZARD_LOCATIONS = ["CNC加工区","SMT车间","冲压车间","焊接区","仓库通道","配电房","空压站","化学品库","成品区","办公区走廊"]

# ── API Client ─────────────────────────────────────────────────────────

class API:
    def __init__(self, base_url: str):
        self.base = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30)
        self.token = ""
        self.tenant_id = ""
        self.user_id = ""
        self.ok = 0
        self.fail = 0

    def login(self):
        r = self.client.post(f"{self.base}/auth/login", json={
            "tenant_code": TENANT, "username": USERNAME, "password": PASSWORD,
        })
        r.raise_for_status()
        self.token = r.json()["access_token"]
        me = self.get("/auth/me")
        self.tenant_id = me["tenant_id"]
        self.user_id = me["id"]

    def _h(self):
        return {"Authorization": f"Bearer {self.token}"}

    def get(self, path, params=None):
        r = self.client.get(f"{self.base}{path}", headers=self._h(), params=params)
        if r.status_code >= 400:
            return None
        return r.json()

    def post(self, path, json=None, params=None, label="", silent=False):
        r = self.client.post(f"{self.base}{path}", headers=self._h(), json=json, params=params)
        if r.status_code >= 400:
            self.fail += 1
            if not silent:
                detail = ""
                try:
                    d = r.json()
                    detail = d.get("detail", "")
                    if isinstance(detail, list):
                        detail = "; ".join(x.get("msg","") for x in detail)
                except Exception:
                    detail = r.text[:100]
                print(f"    FAIL [{r.status_code}] {label or path}: {detail}")
            return None
        self.ok += 1
        return r.json()

    def patch(self, path, json=None, label=""):
        r = self.client.patch(f"{self.base}{path}", headers=self._h(), json=json)
        if r.status_code >= 400:
            self.fail += 1
            return None
        self.ok += 1
        return r.json()


def uid():
    return uuid4().hex[:8]

def rand_name():
    return random.choice(SURNAMES) + random.choice(GIVEN_NAMES) + random.choice(GIVEN_NAMES[:10])

# ── State ──────────────────────────────────────────────────────────────

class S:
    product_ids: dict = {}    # code → id
    bom_ids: dict = {}        # product_code → bom_id
    routing_ids: dict = {}    # product_code → routing_id
    supplier_ids: dict = {}   # code → id
    customer_ids: dict = {}   # code → id
    employee_ids: list = []
    inspector_ids: list = []
    warehouse_ids: dict = {}  # code → id
    account_ids: dict = {}    # code → id
    equipment_ids: list = []
    work_order_ids: list = []
    attendance_done: set = set()

# ── Phase 1: 组织架构 ─────────────────────────────────────────────────

def phase1_employees(api: API):
    print("\n═══ Phase 1: 组织架构 (100名员工) ═══")
    existing = api.get("/mgmt/hr/employees")
    items = existing if isinstance(existing, list) else (existing or {}).get("items", [])
    if len(items) >= 50:
        S.employee_ids = [e["id"] for e in items]
        S.inspector_ids = S.employee_ids[:10]
        print(f"  已有 {len(items)} 员工, 跳过")
        return

    emp_no = 1000
    salaries = {"总经理":35000,"副总经理":28000,"总经理助理":12000,"总监":25000,
                "经理":18000,"主任":14000,"班组长":10000,"工程师":13000,
                "专员":9000,"操作员":7500,"司机":7000,"技师":11000,
                "出纳":9500,"会计":11000,"前台":6500,"代表":8500}
    for dept_code, dept_name, positions in DEPARTMENTS:
        for pos in positions:
            emp_no += 1
            name = rand_name()
            salary = salaries.get(pos, 8000)
            for k, v in salaries.items():
                if k in pos:
                    salary = v
                    break
            r = api.post("/mgmt/hr/employees", {
                "employee_no": f"EMP-{emp_no}",
                "name": name,
                "position": f"{dept_name}-{pos}",
                "base_salary": salary,
            }, label=f"{name}({pos})")
            if r:
                S.employee_ids.append(r["id"])
                if "质检" in pos or "检验" in pos or "SPC" in pos:
                    S.inspector_ids.append(r["id"])

    # 确保有质检员
    if not S.inspector_ids:
        S.inspector_ids = S.employee_ids[:5]

    print(f"  创建 {len(S.employee_ids)} 名员工, {len(S.inspector_ids)} 名质检员")


# ── Phase 2: 产品体系 ─────────────────────────────────────────────────

def phase2_products(api: API):
    print("\n═══ Phase 2: 产品体系 (20个产品 + BOM + 工艺) ═══")
    existing = _extract(api.get("/plm/products", params={"skip":"0","limit":"100"}))
    existing_codes = {p.get("code","?"): p["id"] for p in existing}
    our_codes = {p[0] for p in PRODUCTS_DATA}
    matched = our_codes & set(existing_codes.keys())
    if len(matched) >= 15:
        S.product_ids = existing_codes
        print(f"  已有 {len(matched)}/{len(our_codes)} 个工厂产品, 跳过")
        return
    # Load any existing ones
    S.product_ids.update(existing_codes)

    for code, name, cat, uom, ops in PRODUCTS_DATA:
        r = api.post("/plm/products", {"code": code, "name": name, "category": cat, "uom": uom}, label=code)
        if r:
            S.product_ids[code] = r["id"]

    # BOM for finished products
    finished = [p for p in PRODUCTS_DATA if p[2] == "self_made"]
    raw_codes = [p[0] for p in PRODUCTS_DATA if p[2] in ("raw_material", "agent")]

    for code, name, cat, uom, ops in finished:
        pid = S.product_ids.get(code)
        if not pid:
            continue
        bom = api.post("/plm/bom", {"product_id": pid, "version": "V1.0"}, label=f"BOM-{code}")
        if bom:
            S.bom_ids[code] = bom["id"]
            # Add 3-5 components
            for rc in random.sample(raw_codes, min(4, len(raw_codes))):
                comp_id = S.product_ids.get(rc)
                if comp_id:
                    api.post(f"/plm/bom/{bom['id']}/items", {
                        "component_id": comp_id,
                        "quantity": random.randint(1, 20),
                        "uom": "pcs",
                        "unit_cost": round(random.uniform(2, 80), 2),
                    }, label=f"BOM-item-{rc}")

        # Routing
        if ops:
            rtg = api.post("/plm/routing", {"product_id": pid, "version": "V1.0"}, label=f"RTG-{code}")
            if rtg:
                S.routing_ids[code] = rtg["id"]
                for seq, (op_code, op_name, mins) in enumerate(ops, 1):
                    api.post(f"/plm/routing/{rtg['id']}/operations", {
                        "sequence": seq, "operation_code": op_code,
                        "operation_name": op_name, "standard_minutes": mins,
                        "setup_minutes": random.randint(3, 10),
                    }, label=f"OP-{op_code}")

    print(f"  产品: {len(S.product_ids)}, BOM: {len(S.bom_ids)}, Routing: {len(S.routing_ids)}")


# ── Phase 3: 供应链 ───────────────────────────────────────────────────

def phase3_supply(api: API):
    print("\n═══ Phase 3: 供应链 (10供应商 + 4仓库 + 库位) ═══")
    tp = {"tenant_id": api.tenant_id}

    # Suppliers — skip if already populated
    existing_sup = api.get("/scm/suppliers", params={**tp, "skip": "0", "limit": "50"})
    sup_items = (existing_sup or {}).get("items", existing_sup) if isinstance(existing_sup, (dict, list)) else []
    if isinstance(sup_items, list) and len(sup_items) >= 8:
        S.supplier_ids = {s.get("code", "?"): s["id"] for s in sup_items}
        print(f"  已有 {len(sup_items)} 供应商, 跳过")
    else:
        for code, name, tier, contact, phone, addr in SUPPLIERS_DATA:
            r = api.post("/scm/suppliers", {
                "code": code, "name": name, "tier": tier,
                "contact_name": contact, "contact_phone": phone, "address": addr,
            }, params=tp, label=code)
            if r:
                S.supplier_ids[code] = r["id"]

    # Warehouses — skip if exist
    existing_wh = _extract(api.get("/scm/warehouses", params={**tp, "skip":"0","limit":"50"}))
    if len(existing_wh) >= 3:
        S.warehouse_ids = {w.get("code","?"): w["id"] for w in existing_wh}
        print(f"  已有 {len(existing_wh)} 仓库, 跳过")
    else:
        for code, name, addr in WAREHOUSES_DATA:
            r = api.post("/scm/warehouses", {"code": code, "name": name, "address": addr}, params=tp, label=code)
            if r:
                S.warehouse_ids[code] = r["id"]
                for zone in ["A区", "B区", "C区"]:
                    api.post("/scm/locations", {
                        "warehouse_id": r["id"], "code": f"{code}-{zone[:1]}",
                        "name": zone, "level": "zone",
                    }, params=tp, label=f"{code}/{zone}")

    print(f"  供应商: {len(S.supplier_ids)}, 仓库: {len(S.warehouse_ids)}")


# ── Phase 4: 财务体系 ─────────────────────────────────────────────────

def phase4_finance(api: API):
    print("\n═══ Phase 4: 财务体系 (33个科目 + 期初凭证) ═══")
    existing = api.get("/mgmt/finance/accounts")
    items = existing if isinstance(existing, list) else (existing or {}).get("items", [])
    if len(items) >= 20:
        S.account_ids = {a["code"]: a["id"] for a in items}
        print(f"  已有 {len(items)} 科目, 跳过")
        return
    for code, name, typ in GL_ACCOUNTS_DATA:
        r = api.post("/mgmt/finance/accounts", {"code": code, "name": name, "account_type": typ, "level": 1}, label=code)
        if r:
            S.account_ids[code] = r["id"]

    # 期初余额凭证
    if S.account_ids.get("1002") and S.account_ids.get("3001"):
        api.post("/mgmt/finance/journal", {
            "entry_date": "2026-01-01", "memo": "期初余额-实收资本",
            "lines": [
                {"account_id": S.account_ids["1002"], "debit_amount": 5000000, "credit_amount": 0},
                {"account_id": S.account_ids["3001"], "debit_amount": 0, "credit_amount": 5000000},
            ],
        }, label="期初-实收资本")

    if S.account_ids.get("1501") and S.account_ids.get("1002"):
        api.post("/mgmt/finance/journal", {
            "entry_date": "2026-01-15", "memo": "购入设备",
            "lines": [
                {"account_id": S.account_ids["1501"], "debit_amount": 2000000, "credit_amount": 0},
                {"account_id": S.account_ids["1002"], "debit_amount": 0, "credit_amount": 2000000},
            ],
        }, label="期初-固定资产")

    print(f"  科目: {len(S.account_ids)}")


# ── Phase 5: 客户体系 ─────────────────────────────────────────────────

def phase5_customers(api: API):
    print("\n═══ Phase 5: 客户体系 (15个客户 + 联系人) ═══")
    if S.customer_ids and len(S.customer_ids) >= 10:
        print(f"  已有 {len(S.customer_ids)} 客户, 跳过")
        return
    for code, name, kind, rating in CUSTOMERS_DATA:
        r = api.post("/plm/customers", {"code": code, "name": name, "kind": kind, "rating": rating}, label=code, silent=True)
        if r:
            S.customer_ids[code] = r["id"]
            api.post(f"/plm/customers/{r['id']}/contacts", {
                "name": rand_name(), "title": "采购经理",
                "phone": f"1380000{random.randint(1000,9999)}", "is_primary": True,
            }, silent=True)

    print(f"  客户: {len(S.customer_ids)}")


# ── Phase 6: 设备+能源 ───────────────────────────────────────────────

def phase6_equipment(api: API):
    print("\n═══ Phase 6: 设备与能源 (20台设备 + 5个表计) ═══")
    existing = _extract(api.get("/mfg/equipment"))
    if len(existing) >= 15:
        S.equipment_ids = [e["id"] for e in existing]
        print(f"  已有 {len(existing)} 设备, 跳过")
        return
    workshop_id = str(uuid4())
    for code, name in EQUIPMENT_DATA:
        r = api.post("/mfg/equipment", {
            "code": code, "name": name, "workshop_id": workshop_id, "status": "running",
        }, label=code)
        if r:
            S.equipment_ids.append(r["id"])

    # Energy meters
    for i, (etype, name) in enumerate([
        ("electricity", "总电表"), ("electricity", "生产车间电表"),
        ("water", "总水表"), ("gas", "天然气表"), ("compressed_air", "压缩空气流量计"),
    ]):
        api.post("/mfg/energy/meters", {
            "code": f"MTR-{i+1:03d}", "name": name, "energy_type": etype, "uom": "kWh" if etype == "electricity" else "m³",
        }, label=name)

    print(f"  设备: {len(S.equipment_ids)}")


# ── Phase 7: 审批流程 ─────────────────────────────────────────────────

def phase7_approvals(api: API):
    print("\n═══ Phase 7: 审批流程定义 ═══")
    existing = _extract(api.get("/mgmt/approval/definitions"))
    if len(existing) >= 3:
        print(f"  已有 {len(existing)} 审批流, 跳过")
        return
    approver = api.user_id
    for btype, name in [
        ("purchase_order", "采购审批"), ("tier_change", "供应商等级变更"),
        ("leave_request", "请假审批"), ("expense_claim", "费用报销"),
    ]:
        api.post("/mgmt/approval/definitions", {
            "business_type": btype, "name": name,
            "steps_config": [
                {"step_no": 1, "approver_id": approver, "name": "部门主管"},
                {"step_no": 2, "approver_id": approver, "name": "总经理"},
            ],
        }, label=name)
    print("  审批流定义完成")


# ── Phase 8: 运营模拟 ─────────────────────────────────────────────────

def phase8_operations(api: API, days: int = 30, ticks_per_day: int = 5):
    print(f"\n═══ Phase 8: 运营模拟 ({days}天, 每天{ticks_per_day}轮) ═══")
    tp = {"tenant_id": api.tenant_id}

    # Load IDs if not populated
    _load_ids(api)

    finished_codes = [c for c, _, cat, _, ops in PRODUCTS_DATA if cat == "self_made" and c in S.bom_ids and c in S.product_ids]
    wo_counter = 0
    total_ops = 0

    for day in range(days):
        sim_date = datetime.now() - timedelta(days=days - day)
        date_str = sim_date.strftime("%Y-%m-%d")
        print(f"\n  ── Day {day+1}/{days} [{date_str}] ──")

        # Daily attendance for a subset of employees (avoid flooding)
        day_employees = random.sample(S.employee_ids, min(30, len(S.employee_ids)))
        for eid in day_employees:
            if (eid, date_str) in S.attendance_done:
                continue
            h_in = random.choices([7,8,8,8,9], weights=[5,70,10,10,5])[0]
            m_in = random.randint(0,59)
            h_out = random.choices([17,17,18,19,20], weights=[10,50,25,10,5])[0]
            m_out = random.randint(0,59)
            ot = max(0, h_out - 17 + (m_out/60 if h_out >= 17 else 0))
            api.post("/mgmt/hr/attendance", {
                "employee_id": eid, "work_date": date_str,
                "clock_in": f"{h_in:02d}:{m_in:02d}:00",
                "clock_out": f"{h_out:02d}:{m_out:02d}:00",
                "status": "normal" if h_in <= 8 else "late",
                "work_hours": round(h_out-h_in+(m_out-m_in)/60, 1),
                "overtime_hours": round(ot, 1),
            }, silent=True)
            # Silently ignore duplicate attendance (500 = unique constraint)
            S.attendance_done.add((eid, date_str))

        for tick in range(ticks_per_day):
            total_ops += 1

            # Create work orders (2-3 per day)
            if tick < 3 and finished_codes:
                wo_counter += 1
                code = random.choice(finished_codes)
                pid = S.product_ids[code]
                wo = api.post("/mfg/work-orders", {
                    "order_no": f"WO-{sim_date.strftime('%m%d')}-{uid()}",
                    "product_id": pid,
                    "bom_id": S.bom_ids[code],
                    "routing_id": S.routing_ids.get(code, str(uuid4())),
                    "planned_quantity": {"value": random.choice([100,200,500]), "uom": "pcs"},
                    "planned_start": sim_date.isoformat(),
                    "planned_end": (sim_date + timedelta(days=random.randint(3,10))).isoformat(),
                }, label=f"工单-{code}")
                if wo:
                    S.work_order_ids.append(wo["id"])

            # QC inspections
            if random.random() < 0.6 and S.product_ids and S.inspector_ids:
                pid = S.product_ids[random.choice(list(S.product_ids.keys()))]
                result = random.choices(["pass","conditional"], weights=[93,7])[0]
                api.post("/mfg/qc/inspections", {
                    "inspection_no": f"QC-{uid()}", "type": random.choice(["iqc","ipqc","oqc"]),
                    "product_id": pid, "sample_size": random.choice([30,50,100]),
                    "defect_count": 0 if result == "pass" else random.randint(1,5),
                    "result": result, "inspector_id": random.choice(S.inspector_ids),
                }, label="质检")

            # Purchase orders
            if random.random() < 0.3 and S.supplier_ids and S.product_ids:
                sid = random.choice(list(S.supplier_ids.values()))
                pid = S.product_ids[random.choice(list(S.product_ids.keys()))]
                qty = random.choice([50,100,200,500,1000])
                price = round(random.uniform(5,200), 2)
                api.post("/scm/purchase-orders", {
                    "order_no": f"PO-{uid()}", "supplier_id": sid,
                    "lines": [{"product_id": pid, "quantity": qty, "uom": "pcs", "unit_price": price}],
                }, params=tp, label=f"采购-{qty}pcs")

            # Journal entries
            if random.random() < 0.4 and len(S.account_ids) >= 2:
                codes = list(S.account_ids.keys())
                dc = random.choice(codes)
                cc = random.choice([c for c in codes if c != dc])
                amt = round(random.uniform(500, 80000), 2)
                memos = ["采购原材料","销售收款","发放工资","设备维修","水电费","差旅费","物流运费","办公用品"]
                api.post("/mgmt/finance/journal", {
                    "entry_date": date_str, "memo": random.choice(memos),
                    "lines": [
                        {"account_id": S.account_ids[dc], "debit_amount": amt, "credit_amount": 0},
                        {"account_id": S.account_ids[cc], "debit_amount": 0, "credit_amount": amt},
                    ],
                }, label="凭证")

            # Safety hazards (rare)
            if random.random() < 0.05:
                api.post("/mfg/safety/hazards", {
                    "hazard_no": f"HAZ-{uid()}", "location": random.choice(HAZARD_LOCATIONS),
                    "level": random.choices(["minor","moderate","major","critical"], weights=[50,30,15,5])[0],
                    "description": f"Day{day+1}巡检发现隐患",
                }, silent=True)

    print(f"\n  运营模拟完成: {wo_counter} 工单, {total_ops} 轮")


def _extract(d) -> list:
    """Extract items list from API response (handles both list and paginated dict)."""
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        return d.get("items", [])
    return []

def _load_ids(api: API):
    """从 API 加载已有 ID"""
    tp = {"tenant_id": api.tenant_id}
    if not S.product_ids:
        items = _extract(api.get("/plm/products", params={"skip": "0", "limit": "50"}))
        S.product_ids = {p.get("code", "?"): p["id"] for p in items}
    if not S.supplier_ids:
        items = _extract(api.get("/scm/suppliers", params={**tp, "skip": "0", "limit": "50"}))
        S.supplier_ids = {s.get("code", "?"): s["id"] for s in items}
    if not S.customer_ids:
        items = _extract(api.get("/plm/customers", params={"skip": "0", "limit": "50"}))
        S.customer_ids = {c.get("code", "?"): c["id"] for c in items}
    if not S.employee_ids:
        items = _extract(api.get("/mgmt/hr/employees"))
        S.employee_ids = [e["id"] for e in items]
        S.inspector_ids = S.employee_ids[:10] if S.employee_ids else []
    if not S.account_ids:
        items = _extract(api.get("/mgmt/finance/accounts"))
        S.account_ids = {a["code"]: a["id"] for a in items}
    if not S.equipment_ids:
        items = _extract(api.get("/mfg/equipment"))
        S.equipment_ids = [e["id"] for e in items]
    if not S.warehouse_ids:
        items = _extract(api.get("/scm/warehouses", params={**tp, "skip": "0", "limit": "50"}))
        S.warehouse_ids = {w.get("code", "?"): w["id"] for w in items}

    # Load BOM/Routing IDs — create if missing
    if not S.bom_ids:
        for code in [p[0] for p in PRODUCTS_DATA if p[2] == "self_made"]:
            pid = S.product_ids.get(code)
            if not pid:
                continue
            bom = api.post("/plm/bom", {"product_id": pid, "version": "V1.0"}, silent=True)
            if bom:
                S.bom_ids[code] = bom["id"]
            rtg = api.post("/plm/routing", {"product_id": pid, "version": "V1.0"}, silent=True)
            if rtg:
                S.routing_ids[code] = rtg["id"]
        # If no BOMs were created (all existed), use product IDs as fallback
        if not S.bom_ids:
            for code in [p[0] for p in PRODUCTS_DATA if p[2] == "self_made"]:
                if code in S.product_ids:
                    S.bom_ids[code] = S.product_ids[code]
                    S.routing_ids[code] = S.product_ids[code]


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="100人工厂全场景初始化 + 运营模拟")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--phase", type=int, help="只运行指定阶段 (1-8)")
    parser.add_argument("--skip-to-ops", action="store_true", help="跳过初始化, 直接运营")
    parser.add_argument("--days", type=int, default=30, help="运营模拟天数")
    args = parser.parse_args()

    api = API(args.base_url)

    print("╔══════════════════════════════════════════════════╗")
    print("║  分路链式 V5.0 · 100人工厂全场景模拟             ║")
    print(f"║  API: {args.base_url:<42s}║")
    print("╚══════════════════════════════════════════════════╝")

    print("\n[AUTH] 登录中...")
    try:
        api.login()
        print(f"  OK: {api.tenant_id[:8]}...")
    except Exception as e:
        print(f"  登录失败: {e}")
        sys.exit(1)

    phases = [
        (1, phase1_employees),
        (2, phase2_products),
        (3, phase3_supply),
        (4, phase4_finance),
        (5, phase5_customers),
        (6, phase6_equipment),
        (7, phase7_approvals),
    ]

    if args.skip_to_ops:
        _load_ids(api)
    elif args.phase:
        if args.phase <= 7:
            phases[args.phase - 1][1](api)
        elif args.phase == 8:
            _load_ids(api)
    else:
        for num, fn in phases:
            fn(api)

    if not args.phase or args.phase == 8 or args.skip_to_ops:
        phase8_operations(api, days=args.days)

    print(f"\n{'='*52}")
    print(f"  完成! 成功: {api.ok}  失败: {api.fail}")
    print(f"  成功率: {api.ok / max(api.ok + api.fail, 1) * 100:.1f}%")
    print(f"{'='*52}")


if __name__ == "__main__":
    main()
