"""操作日志中间件 — 自动记录所有 POST/PATCH/DELETE 操作,包含业务详情。"""

from __future__ import annotations

import json
import re
from uuid import UUID, uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Path → (resource, action) 映射规则
PATH_PATTERNS = [
    (r"/plm/products", "plm.product", "create"),
    (r"/plm/customers", "plm.customer", "create"),
    (r"/plm/ecn", "plm.ecn", "create"),
    (r"/plm/service/tickets/.+/transition", "plm.ticket", "transition"),
    (r"/plm/service/tickets/.+/close", "plm.ticket", "close"),
    (r"/plm/service/tickets", "plm.ticket", "create"),
    (r"/plm/bom", "plm.bom", "create"),
    (r"/plm/routing", "plm.routing", "create"),
    (r"/plm/crm/leads", "plm.lead", "create"),
    (r"/plm/crm/opportunities", "plm.opportunity", "create"),
    (r"/plm/crm/quotes", "plm.quote", "create"),
    (r"/mfg/work-orders/.+/status", "mfg.work_order", "transition"),
    (r"/mfg/work-orders", "mfg.work_order", "create"),
    (r"/mfg/job-tickets/.+/report", "mfg.job_ticket", "report"),
    (r"/mfg/job-tickets", "mfg.job_ticket", "create"),
    (r"/mfg/qc/inspections", "mfg.qc_inspection", "create"),
    (r"/mfg/safety/hazards/.+/transition", "mfg.safety_hazard", "transition"),
    (r"/mfg/safety/hazards", "mfg.safety_hazard", "create"),
    (r"/mfg/equipment", "mfg.equipment", "create"),
    (r"/mfg/energy", "mfg.energy", "create"),
    (r"/mfg/aps", "mfg.aps", "create"),
    (r"/scm/suppliers", "scm.supplier", "create"),
    (r"/scm/purchase-orders/.+/transition", "scm.purchase_order", "transition"),
    (r"/scm/purchase-orders", "scm.purchase_order", "create"),
    (r"/scm/purchase-receipts", "scm.receipt", "create"),
    (r"/scm/warehouses", "scm.warehouse", "create"),
    (r"/scm/locations", "scm.location", "create"),
    (r"/scm/stocktakes", "scm.stocktake", "create"),
    (r"/scm/receive", "scm.inventory", "receive"),
    (r"/scm/issue", "scm.inventory", "issue"),
    (r"/mgmt/finance/accounts", "mgmt.gl_account", "create"),
    (r"/mgmt/finance/journal/.+/post", "mgmt.journal", "post"),
    (r"/mgmt/finance/journal", "mgmt.journal", "create"),
    (r"/mgmt/finance/ap", "mgmt.ap", "create"),
    (r"/mgmt/finance/ar", "mgmt.ar", "create"),
    (r"/mgmt/hr/employees", "mgmt.employee", "create"),
    (r"/mgmt/hr/attendance", "mgmt.attendance", "create"),
    (r"/mgmt/hr/payroll/run", "mgmt.payroll", "run"),
    (r"/mgmt/approval/.+/action", "mgmt.approval", "action"),
    (r"/mgmt/approval/definitions", "mgmt.approval_def", "create"),
    (r"/mgmt/approval", "mgmt.approval", "submit"),
    (r"/auth/users", "auth.user", "create"),
    (r"/auth/roles", "auth.role", "create"),
    (r"/sales/.+/confirm", "sales.order", "confirm"),
    (r"/sales/.+/payment", "sales.order", "payment"),
    (r"/sales/.+/ship", "sales.order", "ship"),
    (r"/sales$", "sales.order", "create"),
    (r"/sales/", "sales.order", "create"),
]

# 从请求 body 中提取关键业务信息用于 detail
DETAIL_FIELDS = {
    "sales.order": ["order_no", "customer_name", "total_amount", "amount"],
    "plm.product": ["code", "name"],
    "plm.customer": ["code", "name"],
    "plm.ecn": ["ecn_no", "title"],
    "plm.ticket": ["ticket_no", "description", "nps_score"],
    "mfg.work_order": ["order_no", "status"],
    "mfg.qc_inspection": ["inspection_no", "result"],
    "mfg.safety_hazard": ["hazard_no", "location", "level"],
    "mfg.equipment": ["code", "name"],
    "mfg.job_ticket": ["ticket_no"],
    "scm.supplier": ["code", "name"],
    "scm.purchase_order": ["order_no", "to_status"],
    "scm.warehouse": ["code", "name"],
    "scm.stocktake": ["stocktake_no"],
    "scm.inventory": ["product_id", "quantity", "batch_no"],
    "mgmt.gl_account": ["code", "name"],
    "mgmt.journal": ["memo", "entry_date"],
    "mgmt.employee": ["employee_no", "name"],
    "mgmt.attendance": ["work_date"],
    "mgmt.approval": ["business_type", "action", "comment"],
    "auth.user": ["username", "full_name"],
    "auth.role": ["code", "name"],
}


def _match_resource(path: str, method: str) -> tuple[str | None, str | None]:
    """Match path to resource/action."""
    action = "update" if method == "PATCH" else ("delete" if method == "DELETE" else None)
    for pattern, resource, default_action in PATH_PATTERNS:
        if re.match(pattern, path):
            return resource, action or default_action
    return None, action or "unknown"


def _build_detail(resource: str | None, action: str | None, body: dict | None) -> str:
    """从请求 body 构建人类可读的操作详情。"""
    if not resource or not body:
        return ""

    fields = DETAIL_FIELDS.get(resource, [])
    parts = []
    for f in fields:
        v = body.get(f)
        if v is not None:
            # 截断长值
            sv = str(v)[:60]
            parts.append(f"{f}={sv}")

    if not parts:
        return ""
    return "; ".join(parts)


def _extract_user(request: Request) -> tuple[UUID | None, UUID | None, str | None]:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None, None, None
    try:
        import jwt as pyjwt
        import os
        secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
        payload = pyjwt.decode(auth[7:], secret, algorithms=["HS256"],
                               options={"verify_exp": False})
        return UUID(payload.get("sub", "")), UUID(payload.get("tid", "")), None
    except Exception:
        return None, None, None


class AuditLogMiddleware(BaseHTTPMiddleware):
    """记录所有写操作到 audit_logs 表,包含业务详情。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        if method not in ("POST", "PATCH", "PUT", "DELETE"):
            return await call_next(request)

        path = request.url.path
        if path in ("/health", "/auth/login", "/auth/refresh", "/openapi.json", "/docs", "/redoc"):
            return await call_next(request)

        # 读取 body 用于提取详情（需要缓存以便后续处理）
        body_dict: dict | None = None
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_dict = json.loads(body_bytes)
        except Exception:
            pass

        response = await call_next(request)

        try:
            user_id, tenant_id, _ = _extract_user(request)
            resource, action = _match_resource(path, method)
            detail = _build_detail(resource, action, body_dict)

            from packages.shared.db import get_sessionmaker
            from packages.shared.models.audit_log import AuditLog

            sm = get_sessionmaker()
            async with sm() as session:
                log = AuditLog(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    method=method,
                    path=path[:512],
                    status_code=response.status_code,
                    resource=resource,
                    action=action,
                    detail=detail or None,
                    ip_address=request.client.host if request.client else None,
                )
                session.add(log)
                await session.commit()
        except Exception:
            pass

        return response
