#!/usr/bin/env python3
"""为财务三表填充有意义的记账凭证。"""
import httpx

B = "http://localhost:8000"
c = httpx.Client(timeout=30)
r = c.post(f"{B}/auth/login", json={"tenant_code": "demo", "username": "admin", "password": "admin123"})
h = {"Authorization": f"Bearer {r.json()['access_token']}", "Content-Type": "application/json"}

# Load account IDs
accts = c.get(f"{B}/mgmt/finance/accounts", headers=h).json()
acct_map = {a["code"]: a["id"] for a in accts}

ok = fail = 0
def jrn(date, memo, debit_code, credit_code, amount):
    global ok, fail
    d_id = acct_map.get(debit_code)
    c_id = acct_map.get(credit_code)
    if not d_id or not c_id:
        print(f"  SKIP: {debit_code} or {credit_code} not found")
        fail += 1
        return
    r = c.post(f"{B}/mgmt/finance/journal", headers=h, json={
        "entry_date": date, "memo": memo,
        "lines": [
            {"account_id": d_id, "debit_amount": amount, "credit_amount": 0},
            {"account_id": c_id, "debit_amount": 0, "credit_amount": amount},
        ],
    })
    if r.status_code < 400:
        ok += 1
    else:
        fail += 1
        print(f"  FAIL: {memo}: {r.text[:80]}")

print("=== 资产负债表相关凭证 ===")
# 实收资本 → 银行存款
jrn("2026-04-01", "股东追加投资", "1002", "3001", 1000000)
# 银行借款
jrn("2026-04-02", "短期借款到账", "1002", "2001", 500000)
# 购入原材料（赊购）
jrn("2026-04-03", "采购原材料-铝合金棒料", "1401", "2202", 280000)
jrn("2026-04-05", "采购原材料-电子元器件", "1401", "2202", 150000)
jrn("2026-04-08", "采购原材料-不锈钢板", "1401", "2202", 95000)
# 原材料领用→生产成本
jrn("2026-04-06", "生产领料-智能控制器", "4001", "1401", 180000)
jrn("2026-04-10", "生产领料-电源模块", "4001", "1401", 120000)
# 完工入库
jrn("2026-04-12", "智能控制器完工入库", "1405", "4001", 250000)
jrn("2026-04-15", "电源模块完工入库", "1405", "4001", 160000)
# 预收客户货款
jrn("2026-04-04", "预收华为货款", "1002", "2203", 200000)

print("\n=== 利润表相关凭证 ===")
# 销售收入
jrn("2026-04-10", "销售智能控制器200台", "1122", "6001", 580000)
jrn("2026-04-15", "销售电源模块500台", "1122", "6001", 320000)
jrn("2026-04-18", "销售铝合金壳体1000件", "1122", "6001", 450000)
jrn("2026-04-22", "销售LED驱动板800件", "1122", "6001", 280000)
jrn("2026-04-25", "销售不锈钢底座600件", "1122", "6001", 195000)
# 销售成本
jrn("2026-04-10", "结转销售成本-智能控制器", "6401", "1405", 350000)
jrn("2026-04-15", "结转销售成本-电源模块", "6401", "1405", 180000)
jrn("2026-04-18", "结转销售成本-铝合金壳体", "6401", "1405", 260000)
jrn("2026-04-22", "结转销售成本-LED驱动板", "6401", "1405", 150000)
jrn("2026-04-25", "结转销售成本-不锈钢底座", "6401", "1405", 110000)
# 费用
jrn("2026-04-08", "管理人员工资", "6602", "2211", 180000)
jrn("2026-04-08", "生产人员工资", "4001", "2211", 350000)
jrn("2026-04-08", "销售人员工资+提成", "6601", "2211", 95000)
jrn("2026-04-12", "水电费", "6602", "1002", 28000)
jrn("2026-04-15", "办公费", "6602", "1002", 12000)
jrn("2026-04-20", "差旅费", "6601", "1002", 18000)
jrn("2026-04-25", "设备折旧", "6602", "1502", 45000)
jrn("2026-04-28", "银行利息支出", "6603", "1002", 8500)
# 其他收入
jrn("2026-04-20", "废料处理收入", "1002", "6051", 15000)

print("\n=== 现金流量相关凭证 ===")
# 收回应收
jrn("2026-04-12", "收回华为货款", "1002", "1122", 580000)
jrn("2026-04-20", "收回比亚迪货款", "1002", "1122", 320000)
jrn("2026-04-28", "收回小米货款（部分）", "1002", "1122", 200000)
# 支付应付
jrn("2026-04-15", "支付宝山铝业货款", "2202", "1002", 280000)
jrn("2026-04-22", "支付华强电子货款", "2202", "1002", 150000)
# 支付工资
jrn("2026-04-09", "发放3月工资", "2211", "1002", 520000)
# 缴税
jrn("2026-04-15", "缴纳增值税", "2221", "1002", 65000)
jrn("2026-04-15", "缴纳企业所得税", "6801", "2221", 42000)

print(f"\n完成: {ok} 条凭证, {fail} 失败")

# Verify statements
print("\n=== 验证三表 ===")
for t, name in [("balance_sheet", "资产负债表"), ("income", "利润表"), ("cash_flow", "现金流量表")]:
    r = c.get(f"{B}/mgmt/finance/statements/{t}?period=2026-04", headers=h)
    d = r.json()
    if t == "balance_sheet":
        print(f"  {name}: 资产={d['assets']['total']:,.2f} 负债={d['liabilities']['total']:,.2f} 权益={d['equity']['total']:,.2f} {'✓平衡' if d['balanced'] else '✗不平衡'}")
    elif t == "income":
        print(f"  {name}: 收入={d['revenue']['total']:,.2f} 费用={d['expenses']['total']:,.2f} 净利润={d['net_income']:,.2f}")
    elif t == "cash_flow":
        print(f"  {name}: 经营净额={d['operating']['net']:,.2f} 现金净变动={d['net_cash_change']:,.2f}")
