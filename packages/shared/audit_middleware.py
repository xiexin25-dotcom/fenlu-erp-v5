"""操作日志中间件 — 自动记录所有 POST/PATCH/DELETE 操作。"""

from __future__ import annotations

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
]


def _match_resource(path: str, method: str) -> tuple[str | None, str | None]:
    """Match path to resource/action."""
    if method == "PATCH":
        action = "update"
    elif method == "DELETE":
        action = "delete"
    else:
        action = None

    for pattern, resource, default_action in PATH_PATTERNS:
        if re.match(pattern, path):
            return resource, action or default_action
    return None, action or "unknown"


def _extract_user(request: Request) -> tuple[UUID | None, UUID | None, str | None]:
    """Extract user info from JWT without DB query."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None, None, None
    try:
        import jwt as pyjwt
        import os
        secret = os.getenv("JWT_SECRET", "dev-secret-change-me")
        payload = pyjwt.decode(auth[7:], secret, algorithms=["HS256"],
                               options={"verify_exp": False})
        uid = UUID(payload.get("sub", ""))
        tid = UUID(payload.get("tid", ""))
        return uid, tid, None  # username resolved later if needed
    except Exception:
        return None, None, None


class AuditLogMiddleware(BaseHTTPMiddleware):
    """记录所有写操作到 audit_logs 表。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        # Only log write operations
        if method not in ("POST", "PATCH", "PUT", "DELETE"):
            return await call_next(request)

        # Skip health, login, refresh, static
        path = request.url.path
        if path in ("/health", "/auth/login", "/auth/refresh", "/openapi.json", "/docs", "/redoc"):
            return await call_next(request)

        response = await call_next(request)

        # Log after response
        try:
            user_id, tenant_id, _ = _extract_user(request)
            resource, action = _match_resource(path, method)

            from packages.shared.db import get_engine, get_sessionmaker
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
                    detail=f"{method} {path}" if resource else None,
                    ip_address=request.client.host if request.client else None,
                )
                session.add(log)
                await session.commit()
        except Exception:
            pass  # Never block request due to logging failure

        return response
