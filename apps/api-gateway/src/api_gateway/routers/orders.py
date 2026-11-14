"""Router HTTP do core-orders (ADR-0023). Fino: só traduz HTTP <-> caso de
uso — mesmo padrão de inventory.py/store_settings.py.

A criação de pedido não tem endpoint próprio: acontece dentro do checkout
do carrinho (api_gateway.routers.cart.start_checkout), que já orquestra
core-cart + core-inventory + core-communication (ADR-0002: cores não se
importam entre si, a orquestração vive no api-gateway)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api_gateway.dependencies import get_inventory_repository, get_order_repository
from api_gateway.orchestration import fulfill_order_stock
from api_gateway.security import require_any_role
from core_identity.domain import AuthenticatedUser, Role
from core_inventory.ports import InventoryRepository
from core_orders.domain import InvalidOrderTransition, Order, OrderNotFound, PaymentStatus
from core_orders.ports import OrderRepository
from core_orders.schemas import (
    OrderLineSchema,
    OrderPageSchema,
    OrderSchema,
    UpdateFulfillmentStatusRequestSchema,
    UpdatePaymentStatusRequestSchema,
)
from core_orders.use_cases import (
    CancelOrder,
    GetOrder,
    ListOrders,
    MarkOrderDelivered,
    MarkOrderPaid,
    MarkOrderShipped,
)

router = APIRouter(prefix="/api/orders", tags=["orders"])


def _to_schema(order: Order) -> OrderSchema:
    return OrderSchema(
        order_id=order.order_id,
        cart_id=order.cart_id,
        lines=[
            OrderLineSchema(
                sku=line.sku,
                product_name=line.product_name,
                variant_label=line.variant_label,
                unit_price=line.unit_price.amount,
                quantity=line.quantity,
                subtotal=line.subtotal().amount,
            )
            for line in order.lines
        ],
        total=order.total().amount,
        currency=order.currency,
        payment_status=order.payment_status.value,
        fulfillment_status=order.fulfillment_status.value,
        created_at=order.created_at,
    )


@router.get("", response_model=OrderPageSchema)
async def list_orders(
    page: int = 1,
    page_size: int = 20,
    payment_status: PaymentStatus | None = None,
    repository: OrderRepository = Depends(get_order_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(Role.STAFF, Role.ADMIN)),
) -> OrderPageSchema:
    """Só STAFF/ADMIN (mesmo nível de core-inventory) — é o que fecha a
    tela de "gestão de pedidos" do admin-dashboard."""
    items, total = await ListOrders(repository).execute(
        payment_status=payment_status, page=page, page_size=page_size
    )
    return OrderPageSchema(
        items=[_to_schema(o) for o in items], page=page, page_size=page_size, total=total
    )


@router.get("/{order_id}", response_model=OrderSchema)
async def get_order(
    order_id: str, repository: OrderRepository = Depends(get_order_repository)
) -> OrderSchema:
    """Sem RBAC de propósito — order_id funciona como token de capacidade,
    mesmo padrão de cart_id (ver api_gateway.routers.cart): o cliente
    acompanha o próprio pedido sem precisar de conta/login."""
    try:
        order = await GetOrder(repository).execute(order_id)
    except OrderNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_schema(order)


@router.patch("/{order_id}/payment-status", response_model=OrderSchema)
async def update_payment_status(
    order_id: str,
    body: UpdatePaymentStatusRequestSchema,
    repository: OrderRepository = Depends(get_order_repository),
    inventory_repository: InventoryRepository = Depends(get_inventory_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(Role.STAFF, Role.ADMIN)),
) -> OrderSchema:
    """Confirmação manual do pagamento (ADR-0023) — a Nick confere pelo
    WhatsApp/Pix e marca aqui. O webhook do Mercado Pago (ADR-0024,
    api_gateway.routers.payments) chama os mesmos casos de uso
    automaticamente quando a cobrança confirma, sem mudar este endpoint —
    este continua sendo o fallback manual."""
    use_case = MarkOrderPaid(repository) if body.action == "mark_paid" else CancelOrder(repository)
    try:
        order = await use_case.execute(order_id)
    except OrderNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if body.action == "mark_paid":
        await fulfill_order_stock(order, inventory_repository)
    return _to_schema(order)


@router.patch("/{order_id}/fulfillment-status", response_model=OrderSchema)
async def update_fulfillment_status(
    order_id: str,
    body: UpdateFulfillmentStatusRequestSchema,
    repository: OrderRepository = Depends(get_order_repository),
    _staff: AuthenticatedUser = Depends(require_any_role(Role.STAFF, Role.ADMIN)),
) -> OrderSchema:
    use_case = (
        MarkOrderShipped(repository) if body.action == "mark_shipped" else MarkOrderDelivered(repository)
    )
    try:
        order = await use_case.execute(order_id)
    except OrderNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _to_schema(order)
