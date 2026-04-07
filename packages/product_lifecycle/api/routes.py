"""Lane 1 · PLM API routes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from packages.shared.auth import CurrentUser
from packages.shared.contracts.base import Page
from packages.shared.db import get_session

from .schemas import (
    BOMCreate,
    BOMItemCreate,
    BOMItemOut,
    BOMOut,
    CadAttachmentOut,
    ContactCreate,
    ContactOut,
    Customer360Out,
    CustomerCreate,
    CustomerOut,
    ECNCreate,
    ECNOut,
    ECNTransition,
    FunnelOut,
    LeadCreate,
    LeadOut,
    LeadTransition,
    OpportunityCreate,
    OpportunityOut,
    OpportunityTransition,
    ProductCreate,
    ProductOut,
    ProductVersionCreate,
    ProductVersionOut,
    QuoteCreate,
    QuoteItemCreate,
    QuoteItemOut,
    QuoteOut,
    QuoteTransition,
    RoutingCreate,
    RoutingOperationCreate,
    RoutingOperationOut,
    RoutingOut,
    SalesOrderLineOut,
    SalesOrderOut,
    TicketClose,
    TicketCreate,
    TicketOut,
    TicketTransition,
)

router = APIRouter(prefix="/plm", tags=["product-lifecycle"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "lane": "product_lifecycle"}


# ── Products ──────────────────────────────────────────────────────────────── #


@router.post("/products", response_model=ProductOut, status_code=201)
async def create_product(
    body: ProductCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ProductOut:
    from packages.product_lifecycle.services.product_service import (
        create_product as _create,
    )

    product = await _create(
        session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        code=body.code,
        name=body.name,
        category=body.category.value,
        uom=body.uom,
        description=body.description,
    )
    return ProductOut.model_validate(product)


@router.get("/products", response_model=Page[ProductOut])
async def list_products(
    user: CurrentUser,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> Page[ProductOut]:
    from packages.product_lifecycle.services.product_service import (
        list_products as _list,
    )

    items, total = await _list(session, tenant_id=user.tenant_id, page=page, size=size)
    return Page[ProductOut](
        items=[ProductOut.model_validate(p) for p in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/products/{product_id}", response_model=ProductOut)
async def get_product(
    product_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ProductOut:
    from packages.product_lifecycle.services.product_service import (
        get_product as _get,
    )

    product = await _get(session, tenant_id=user.tenant_id, product_id=product_id)
    if product is None:
        raise HTTPException(404, "product not found")
    return ProductOut.model_validate(product)


# ── Versions ──────────────────────────────────────────────────────────────── #


@router.post(
    "/products/{product_id}/versions",
    response_model=ProductVersionOut,
    status_code=201,
)
async def create_version(
    product_id: UUID,
    body: ProductVersionCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ProductVersionOut:
    from packages.product_lifecycle.services.product_service import (
        create_version as _create_ver,
    )

    try:
        ver = await _create_ver(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            product_id=product_id,
            change_summary=body.change_summary,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return ProductVersionOut.model_validate(ver)


# ── BOM ───────────────────────────────────────────────────────────────────── #


def _bom_to_out(bom: object, total_cost_amount: object = None) -> BOMOut:
    """Convert BOM ORM → BOMOut, enriching component code/name from relationship."""
    from packages.product_lifecycle.models import BOM as BOMModel

    assert isinstance(bom, BOMModel)
    items_out = []
    for item in bom.items:
        items_out.append(
            BOMItemOut(
                id=item.id,
                component_id=item.component_id,
                component_code=item.component.code if item.component else "",
                component_name=item.component.name if item.component else "",
                quantity=item.quantity,
                uom=item.uom,
                scrap_rate=item.scrap_rate,
                unit_cost=item.unit_cost,
                is_optional=item.is_optional,
                remark=item.remark,
            )
        )
    from decimal import Decimal

    from packages.shared.contracts.base import Money

    tc = None
    if total_cost_amount is not None and isinstance(total_cost_amount, Decimal):
        tc = Money(amount=total_cost_amount)

    return BOMOut(
        id=bom.id,
        product_id=bom.product_id,
        product_code=bom.product.code if bom.product else "",
        version=bom.version,
        status=bom.status,
        description=bom.description,
        items=items_out,
        total_cost=tc,
        created_at=bom.created_at,
        updated_at=bom.updated_at,
    )


@router.post("/bom", response_model=BOMOut, status_code=201)
async def create_bom(
    body: BOMCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> BOMOut:
    from packages.product_lifecycle.services.bom_service import create_bom as _create

    bom = await _create(
        session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        product_id=body.product_id,
        version=body.version,
        description=body.description,
    )
    # re-fetch with relationships
    from packages.product_lifecycle.services.bom_service import get_bom

    bom = await get_bom(session, tenant_id=user.tenant_id, bom_id=bom.id)
    assert bom is not None
    return _bom_to_out(bom)


@router.get("/bom/{bom_id}", response_model=BOMOut)
async def get_bom_detail(
    bom_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> BOMOut:
    from packages.product_lifecycle.services.bom_service import get_bom, rollup_cost

    bom = await get_bom(session, tenant_id=user.tenant_id, bom_id=bom_id)
    if bom is None:
        raise HTTPException(404, "BOM not found")
    cost = await rollup_cost(session, bom)
    return _bom_to_out(bom, cost)


@router.post("/bom/{bom_id}/items", response_model=BOMItemOut, status_code=201)
async def add_bom_item(
    bom_id: UUID,
    body: BOMItemCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> BOMItemOut:
    from packages.product_lifecycle.services.bom_service import (
        CycleDetectedError,
        add_bom_item as _add,
    )

    try:
        item = await _add(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            bom_id=bom_id,
            component_id=body.component_id,
            quantity=body.quantity,
            uom=body.uom,
            scrap_rate=body.scrap_rate,
            unit_cost=body.unit_cost,
            is_optional=body.is_optional,
            remark=body.remark,
        )
    except CycleDetectedError as e:
        raise HTTPException(422, str(e)) from e
    except ValueError as e:
        raise HTTPException(404, str(e)) from e

    # re-fetch to get component relationship
    from packages.product_lifecycle.services.bom_service import get_bom

    bom = await get_bom(session, tenant_id=user.tenant_id, bom_id=bom_id)
    assert bom is not None
    for it in bom.items:
        if it.id == item.id:
            return BOMItemOut(
                id=it.id,
                component_id=it.component_id,
                component_code=it.component.code if it.component else "",
                component_name=it.component.name if it.component else "",
                quantity=it.quantity,
                uom=it.uom,
                scrap_rate=it.scrap_rate,
                unit_cost=it.unit_cost,
                is_optional=it.is_optional,
                remark=it.remark,
            )
    # fallback (shouldn't happen)
    return BOMItemOut.model_validate(item)


# ── CAD Attachments ───────────────────────────────────────────────────────── #


@router.post(
    "/products/{product_id}/cad",
    response_model=CadAttachmentOut,
    status_code=201,
)
async def upload_cad(
    product_id: UUID,
    file: UploadFile,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> CadAttachmentOut:
    from packages.product_lifecycle.services.cad_service import upload_cad as _upload

    if not file.filename:
        raise HTTPException(400, "filename is required")

    file_data = await file.read()
    if len(file_data) == 0:
        raise HTTPException(400, "empty file")

    try:
        attachment = await _upload(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            product_id=product_id,
            filename=file.filename,
            file_data=file_data,
            content_type=file.content_type or "application/octet-stream",
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return CadAttachmentOut.model_validate(attachment)


@router.get(
    "/products/{product_id}/cad",
    response_model=list[CadAttachmentOut],
)
async def list_cad_attachments(
    product_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> list[CadAttachmentOut]:
    from packages.product_lifecycle.services.cad_service import (
        list_cad_attachments as _list,
    )

    items = await _list(session, tenant_id=user.tenant_id, product_id=product_id)
    return [CadAttachmentOut.model_validate(a) for a in items]


# ── Routing ───────────────────────────────────────────────────────────────── #


def _routing_to_out(routing: object) -> RoutingOut:
    from packages.product_lifecycle.models import Routing as RoutingModel

    assert isinstance(routing, RoutingModel)
    ops = [RoutingOperationOut.model_validate(op) for op in routing.operations]
    total = sum(op.standard_minutes for op in ops)
    return RoutingOut(
        id=routing.id,
        product_id=routing.product_id,
        version=routing.version,
        description=routing.description,
        operations=ops,
        total_standard_minutes=total,
        created_at=routing.created_at,
        updated_at=routing.updated_at,
    )


@router.post("/routing", response_model=RoutingOut, status_code=201)
async def create_routing(
    body: RoutingCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> RoutingOut:
    from packages.product_lifecycle.services.routing_service import (
        create_routing as _create,
        get_routing,
    )

    routing = await _create(
        session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        product_id=body.product_id,
        version=body.version,
        description=body.description,
    )
    routing = await get_routing(session, tenant_id=user.tenant_id, routing_id=routing.id)
    assert routing is not None
    return _routing_to_out(routing)


@router.get("/routing/{routing_id}", response_model=RoutingOut)
async def get_routing_detail(
    routing_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> RoutingOut:
    """供 Lane 2 APS 排程调用。"""
    from packages.product_lifecycle.services.routing_service import get_routing

    routing = await get_routing(session, tenant_id=user.tenant_id, routing_id=routing_id)
    if routing is None:
        raise HTTPException(404, "routing not found")
    return _routing_to_out(routing)


@router.post(
    "/routing/{routing_id}/operations",
    response_model=RoutingOperationOut,
    status_code=201,
)
async def add_routing_operation(
    routing_id: UUID,
    body: RoutingOperationCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> RoutingOperationOut:
    from packages.product_lifecycle.services.routing_service import add_operation

    try:
        op = await add_operation(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            routing_id=routing_id,
            sequence=body.sequence,
            operation_code=body.operation_code,
            operation_name=body.operation_name,
            standard_minutes=body.standard_minutes,
            setup_minutes=body.setup_minutes,
            workstation_code=body.workstation_code,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return RoutingOperationOut.model_validate(op)


# ── ECN ───────────────────────────────────────────────────────────────────── #


@router.post("/ecn", response_model=ECNOut, status_code=201)
async def create_ecn(
    body: ECNCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ECNOut:
    from packages.product_lifecycle.services.ecn_service import create_ecn as _create

    try:
        ecn = await _create(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            product_id=body.product_id,
            ecn_no=body.ecn_no,
            title=body.title,
            reason=body.reason,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return ECNOut.model_validate(ecn)


@router.get("/ecn/{ecn_id}", response_model=ECNOut)
async def get_ecn_detail(
    ecn_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ECNOut:
    from packages.product_lifecycle.services.ecn_service import get_ecn

    ecn = await get_ecn(session, tenant_id=user.tenant_id, ecn_id=ecn_id)
    if ecn is None:
        raise HTTPException(404, "ECN not found")
    return ECNOut.model_validate(ecn)


@router.post("/ecn/{ecn_id}/transition", response_model=ECNOut)
async def transition_ecn(
    ecn_id: UUID,
    body: ECNTransition,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ECNOut:
    from packages.product_lifecycle.services.ecn_service import (
        InvalidTransitionError,
        transition_ecn as _transition,
    )

    try:
        ecn = await _transition(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            ecn_id=ecn_id,
            target_status=body.target_status,
        )
    except InvalidTransitionError as e:
        raise HTTPException(422, str(e)) from e
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return ECNOut.model_validate(ecn)


# ── Customer / CRM ────────────────────────────────────────────────────────── #


@router.post("/customers", response_model=CustomerOut, status_code=201)
async def create_customer(
    body: CustomerCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> CustomerOut:
    from packages.product_lifecycle.services.customer_service import (
        create_customer as _create,
        get_customer,
    )

    cust = await _create(
        session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        code=body.code,
        name=body.name,
        kind=body.kind,
        rating=body.rating,
        is_online=body.is_online,
        address=body.address,
    )
    # re-fetch with selectinload(contacts)
    cust = await get_customer(session, tenant_id=user.tenant_id, customer_id=cust.id)
    assert cust is not None
    return CustomerOut.model_validate(cust)


@router.get("/customers/{customer_id}", response_model=CustomerOut)
async def get_customer_detail(
    customer_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> CustomerOut:
    from packages.product_lifecycle.services.customer_service import get_customer

    cust = await get_customer(session, tenant_id=user.tenant_id, customer_id=customer_id)
    if cust is None:
        raise HTTPException(404, "customer not found")
    return CustomerOut.model_validate(cust)


@router.post(
    "/customers/{customer_id}/contacts",
    response_model=ContactOut,
    status_code=201,
)
async def add_contact(
    customer_id: UUID,
    body: ContactCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> ContactOut:
    from packages.product_lifecycle.services.customer_service import (
        add_contact as _add,
    )

    contact = await _add(
        session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        customer_id=customer_id,
        name=body.name,
        title=body.title,
        phone=body.phone,
        email=body.email,
        is_primary=body.is_primary,
    )
    return ContactOut.model_validate(contact)


@router.get("/customers/{customer_id}/360", response_model=Customer360Out)
async def customer_360(
    customer_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> Customer360Out:
    from packages.product_lifecycle.services.customer_service import (
        get_customer_360,
    )

    result = await get_customer_360(
        session, tenant_id=user.tenant_id, customer_id=customer_id,
    )
    if result is None:
        raise HTTPException(404, "customer not found")
    return Customer360Out(
        customer=CustomerOut.model_validate(result.customer),
        counts=result.counts,
        recent_activities=result.recent_activities,
    )


# ── Lead ──────────────────────────────────────────────────────────────────── #


@router.post("/crm/leads", response_model=LeadOut, status_code=201)
async def create_lead(
    body: LeadCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> LeadOut:
    from packages.product_lifecycle.services.crm_service import create_lead as _create

    lead = await _create(
        session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        customer_id=body.customer_id,
        title=body.title,
        source=body.source,
    )
    return LeadOut.model_validate(lead)


@router.post("/crm/leads/{lead_id}/transition", response_model=LeadOut)
async def transition_lead(
    lead_id: UUID,
    body: LeadTransition,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> LeadOut:
    from packages.product_lifecycle.services.crm_service import (
        InvalidStageTransitionError,
        transition_lead as _transition,
    )

    try:
        lead = await _transition(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            lead_id=lead_id,
            target_status=body.target_status,
        )
    except InvalidStageTransitionError as e:
        raise HTTPException(422, str(e)) from e
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return LeadOut.model_validate(lead)


# ── Opportunity ───────────────────────────────────────────────────────────── #


@router.post("/crm/opportunities", response_model=OpportunityOut, status_code=201)
async def create_opportunity(
    body: OpportunityCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> OpportunityOut:
    from packages.product_lifecycle.services.crm_service import (
        create_opportunity as _create,
    )

    opp = await _create(
        session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        customer_id=body.customer_id,
        title=body.title,
        expected_amount=body.expected_amount,
        expected_close=body.expected_close,
    )
    return OpportunityOut.model_validate(opp)


@router.post("/crm/opportunities/{opp_id}/transition", response_model=OpportunityOut)
async def transition_opportunity(
    opp_id: UUID,
    body: OpportunityTransition,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> OpportunityOut:
    from packages.product_lifecycle.services.crm_service import (
        InvalidStageTransitionError,
        transition_opportunity as _transition,
    )

    try:
        opp = await _transition(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            opp_id=opp_id,
            target_stage=body.target_stage,
        )
    except InvalidStageTransitionError as e:
        raise HTTPException(422, str(e)) from e
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return OpportunityOut.model_validate(opp)


# ── Funnel ────────────────────────────────────────────────────────────────── #


@router.get("/crm/funnel", response_model=FunnelOut)
async def get_funnel(
    user: CurrentUser,
    period_start: datetime | None = Query(None),
    period_end: datetime | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> FunnelOut:
    from packages.product_lifecycle.services.crm_service import get_funnel as _get

    result = await _get(
        session,
        tenant_id=user.tenant_id,
        period_start=period_start,
        period_end=period_end,
    )
    return FunnelOut(**result)


# ── Quote ─────────────────────────────────────────────────────────────────── #


@router.post("/crm/quotes", response_model=QuoteOut, status_code=201)
async def create_quote(
    body: QuoteCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> QuoteOut:
    from packages.product_lifecycle.services.order_service import (
        create_quote as _create,
        get_quote,
    )

    quote = await _create(
        session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        customer_id=body.customer_id,
        quote_no=body.quote_no,
        currency=body.currency,
        valid_until=body.valid_until,
        remark=body.remark,
    )
    quote = await get_quote(session, tenant_id=user.tenant_id, quote_id=quote.id)
    assert quote is not None
    return QuoteOut.model_validate(quote)


@router.get("/crm/quotes/{quote_id}", response_model=QuoteOut)
async def get_quote_detail(
    quote_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> QuoteOut:
    from packages.product_lifecycle.services.order_service import get_quote

    quote = await get_quote(session, tenant_id=user.tenant_id, quote_id=quote_id)
    if quote is None:
        raise HTTPException(404, "quote not found")
    return QuoteOut.model_validate(quote)


@router.post("/crm/quotes/{quote_id}/items", response_model=QuoteItemOut, status_code=201)
async def add_quote_item(
    quote_id: UUID,
    body: QuoteItemCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> QuoteItemOut:
    from packages.product_lifecycle.services.order_service import add_quote_item as _add

    try:
        item = await _add(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            quote_id=quote_id,
            product_id=body.product_id,
            quantity=body.quantity,
            uom=body.uom,
            unit_price=body.unit_price,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return QuoteItemOut.model_validate(item)


@router.post("/crm/quotes/{quote_id}/transition", response_model=QuoteOut)
async def transition_quote(
    quote_id: UUID,
    body: QuoteTransition,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> QuoteOut:
    from packages.product_lifecycle.services.order_service import (
        InvalidQuoteTransitionError,
        transition_quote as _transition,
    )

    try:
        quote = await _transition(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            quote_id=quote_id,
            target_status=body.target_status,
            promised_delivery=body.promised_delivery,
        )
    except InvalidQuoteTransitionError as e:
        raise HTTPException(422, str(e)) from e
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return QuoteOut.model_validate(quote)


# ── SalesOrder ────────────────────────────────────────────────────────────── #


@router.get("/crm/orders/{order_id}", response_model=SalesOrderOut)
async def get_order_detail(
    order_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> SalesOrderOut:
    from packages.product_lifecycle.services.order_service import get_sales_order

    order = await get_sales_order(session, tenant_id=user.tenant_id, order_id=order_id)
    if order is None:
        raise HTTPException(404, "order not found")
    return SalesOrderOut.model_validate(order)


# ── ServiceTicket ─────────────────────────────────────────────────────────── #


@router.post("/service/tickets", response_model=TicketOut, status_code=201)
async def create_ticket(
    body: TicketCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> TicketOut:
    from packages.product_lifecycle.services.ticket_service import (
        create_ticket as _create,
    )

    try:
        ticket = await _create(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            customer_id=body.customer_id,
            ticket_no=body.ticket_no,
            product_id=body.product_id,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return TicketOut.model_validate(ticket)


@router.get("/service/tickets/{ticket_id}", response_model=TicketOut)
async def get_ticket_detail(
    ticket_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> TicketOut:
    from packages.product_lifecycle.services.ticket_service import get_ticket

    ticket = await get_ticket(session, tenant_id=user.tenant_id, ticket_id=ticket_id)
    if ticket is None:
        raise HTTPException(404, "ticket not found")
    return TicketOut.model_validate(ticket)


@router.post("/service/tickets/{ticket_id}/transition", response_model=TicketOut)
async def transition_ticket(
    ticket_id: UUID,
    body: TicketTransition,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> TicketOut:
    from packages.product_lifecycle.services.ticket_service import (
        InvalidTicketTransitionError,
        transition_ticket as _transition,
    )

    try:
        ticket = await _transition(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            ticket_id=ticket_id,
            target_status=body.target_status,
        )
    except InvalidTicketTransitionError as e:
        raise HTTPException(422, str(e)) from e
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
    return TicketOut.model_validate(ticket)


@router.post("/service/tickets/{ticket_id}/close", response_model=TicketOut)
async def close_ticket(
    ticket_id: UUID,
    body: TicketClose,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session),
) -> TicketOut:
    from packages.product_lifecycle.services.ticket_service import (
        InvalidTicketTransitionError,
        close_ticket as _close,
    )

    try:
        ticket = await _close(
            session,
            tenant_id=user.tenant_id,
            user_id=user.id,
            ticket_id=ticket_id,
            nps_score=body.nps_score,
        )
    except InvalidTicketTransitionError as e:
        raise HTTPException(422, str(e)) from e
    except ValueError as e:
        raise HTTPException(
            404 if "not found" in str(e) else 422, str(e)
        ) from e
    return TicketOut.model_validate(ticket)
