# 分路链式工业互联网系统 V5.0

> 项目交接文档。新 Claude Code session 进入本仓库时先读此文件。

## 项目概述
工信部三级集成级 ERP 系统，覆盖 16 项应用场景，102 个 commits。
- **后端**: FastAPI + PostgreSQL 16 + Redis 7 + MinIO
- **前端**: React 18 + Vite + Tailwind CSS 4 + Recharts + Lucide Icons
- **部署**: Docker Compose + nginx + 一键脚本

## 技术栈
- Python 3.12, uv, SQLAlchemy 2.0 async, asyncpg, Alembic, Pydantic v2
- TypeScript 5, React Router v7, TanStack Query 5, Zustand 5
- 前端路径: `apps/web-shell/src/`
- 后端路径: `packages/` (4个Lane模块) + `apps/api_gateway/`

## 运行方式
```bash
make up                              # postgres + redis + minio
make migrate                         # alembic migrations
make dev                             # backend :8000
cd apps/web-shell && pnpm dev        # frontend :5173
# 生产部署
bash scripts/deploy.sh               # Docker 全栈部署 :80
```

## 登录账号
| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 系统管理员 |
| zhangwei | zhang123 | 生产主管 |
| lina | li123 | 质检员 |
| wangfang | wang123 | 仓储主管 |
| chenming | chen123 | 财务人员 |
| liuyang | liu123 | 销售人员 |
租户编码统一为 `demo`

## 模块结构
| 模块 | 路由前缀 | 代码位置 |
|------|---------|---------|
| PLM 产品生命周期 | /plm | packages/product_lifecycle/ |
| MFG 生产制造 | /mfg | packages/production/ |
| SCM 供应链 | /scm | packages/supply_chain/ |
| MGMT 管理决策 | /mgmt | packages/management_decision/ |
| Sales 销售管理 | /sales | apps/api_gateway/routers/sales.py |
| Auth 用户+角色+审计日志 | /auth | apps/api_gateway/routers/auth.py |

## 前端页面 (30+)
- 驾驶舱: `src/pages/Dashboard.tsx`
- 销售管理: `src/pages/SalesPage.tsx` (订单+收款+发货+统计)
- PLM: PlmPage + plm/ (产品、BOM、ECN、客户、商机漏斗、售后工单)
- MFG: MfgPage + mfg/ (工单、报工、质检、设备、安全、能耗、APS)
- SCM: ScmPage + scm/ (供应商、采购、仓库、库存入库出库、盘点)
- MGMT: MgmtPage + mgmt/ (科目、凭证、AP/AR、三表、员工、考勤、工资五险一金、KPI、审批、用户管理、操作日志)
- 侧边栏: `src/components/Layout.tsx`
- 路由: `src/App.tsx`
- 共享组件: `src/components/` (DataTable, StatusBadge, PageHeader, FormDialog, ModuleCard)

## 数据库
- 数据库 dump: `data/fenlu_v5_dump.sql` (6.5MB)
- 恢复: `psql -U fenlu -d fenlu_v5 < data/fenlu_v5_dump.sql`
- 一年运营数据: 92员工, 1590工单, 1818质检, 1262凭证(已过账), 12366考勤, 21销售订单

## 已实现的关键功能
- 五险一金按吉林省标准计算 (`packages/management_decision/services/hr.py`)
- 操作审计日志中间件 (`packages/shared/audit_middleware.py`) — 所有写操作自动留痕
- 用户+角色权限管理 (6角色, RBAC via Casbin)
- 财务三表 (`services/statements.py`) — 注意: account_type 大小写已修复(DB存大写,代码用小写)
- 销售订单三重状态: order_status + payment_status + shipment_status
- 销售→AR 自动关联 (创建销售订单自动生成应收记录)
- KPI 20项指标 + 数据点 + rollup聚合
- Apple 简约风 UI (方角, 毛玻璃侧边栏, 柔和配色)

## 已知问题 / 注意事项
- `SalesOrder` 模型重名: PLM 有旧的 SalesOrder, 新的销售模块用 `SalesDoc` (`packages/shared/models/sales_order.py`)
- SCM 所有 API 需要 `tenant_id` query parameter (前端通过 localStorage 自动注入)
- MFG 工单 `planned→released` 转换需要 BOM 验证连 Lane 1 (单服务器模式下会失败)
- 安全隐患创建可能 500 (Redis Streams event emission)
- Decimal 值从后端返回为字符串, 前端需 parseFloat

## 测试脚本
```bash
uv run python scripts/e2e_test.py          # 16条API流程测试
uv run python scripts/test_all_forms.py    # 18个新建表单测试
uv run python scripts/factory_bootstrap.py  # 100人工厂模拟
uv run python scripts/simulator.py --interval 5  # 持续模拟器
cd apps/web-shell && pnpm e2e              # Playwright浏览器测试
```

## 待做 (按优先级)
1. **UI重构**: 参考截图改为左侧可展开菜单树 + 工作台风格首页 + 绿色主题配色
2. **企业微信/钉钉集成**: SSO + 考勤同步 + 消息通知 (方案已设计, 见对话记录)
3. **业财自动联动**: 生产完工/采购入库/销售发货 → 自动生成会计凭证
4. **碳排放核算**: 万元产值综合能耗(tce/万元), 绿色低碳报告
5. **移动端/扫码报工**: H5/小程序, 条码扫码
6. **APS增强**: 甘特图, What-If模拟, 多约束排程
7. **全链路质量追溯**: SN序列号 → 正向/反向追溯

## GitHub
https://github.com/xiexin25-dotcom/fenlu-erp-v5
