"""Router HTTP do core-payments (ADR-0024). Fino: só traduz HTTP <-> caso de
uso — mesmo padrão de orders.py.

Uma cobrança é sempre aberta a partir de um pedido já existente
(core-orders, ADR-0023). A ponte order->charge (na criação) e charge->order
(no webhook, quando a cobrança confirma) vive aqui porque core-payments e
core-orders não se importam entre si (ADR-0002: orquestração cross-core só
no api-gateway)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from api_gateway.dependencies import (
    get_charge_repository,
    get_inventory_repository,
    get_order_repository,
    get_payment_gateway,
)
from api_gateway.orchestration import fulfill_order_stock
from core_inventory.ports import InventoryRepository
from core_orders.domain import OrderNotFound, PaymentStatus
from core_orders.ports import OrderRepository
from core_orders.use_cases import GetOrder, MarkOrderPaid
from core_payments.domain import Charge, ChargeNotFound, PaymentMethod
from core_payments.domain import Money as PaymentsMoney
from core_payments.ports import ChargeRepository, PaymentGateway
from core_payments.schemas import ChargeSchema, CreateChargeRequestSchema
from core_payments.use_cases import ConfirmChargeFromWebhook, CreateCharge, GetChargeByOrder

router = APIRouter(prefix="/api/orders/{order_id}/charges", tags=["payments"])
webhook_router = APIRouter(prefix="/api/payments/webhooks", tags=["payments"])


def _to_schema(charge: Charge) -> ChargeSchema:
    return ChargeSchema(
        charge_id=charge.charge_id,
        order_id=charge.order_id,
        provider=charge.provider,
        method=charge.method.value,
        amount=charge.amount.amount,
        currency=charge.amount.currency,
        status=charge.status.value,
        pix_qr_code=charge.pix_qr_code,
        pix_copy_paste=charge.pix_copy_paste,
        checkout_url=charge.checkout_url,
        created_at=charge.created_at,
    )


@router.post("", response_model=ChargeSchema)
async def create_charge(
    order_id: str,
    body: CreateChargeRequestSchema,
    order_repository: OrderRepository = Depends(get_order_repository),
    charge_repository: ChargeRepository = Depends(get_charge_repository),
    gateway: PaymentGateway = Depends(get_payment_gateway),
) -> ChargeSchema:
    """Sem RBAC de propósito — order_id é token de capacidade, mesmo padrão
    de api_gateway.routers.orders.get_order: o cliente abre a própria
    cobrança sem conta/login."""
    try:
        order = await GetOrder(order_repository).execute(order_id)
    except OrderNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    order_total = order.total()
    amount = PaymentsMoney(order_total.amount, order_total.currency)
    method = PaymentMethod(body.method)
    try:
        charge = await CreateCharge(gateway, charge_repository).execute(
            order_id=order_id, amount=amount, method=method
        )
    except NotImplementedError as exc:
        # Cartão via Mercado Pago ainda não está implementado nesta onda
        # (ver adapters_external.payments.mercado_pago_gateway e ADR-0024).
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    return _to_schema(charge)


@router.get("", response_model=ChargeSchema)
async def get_charge_for_order(
    order_id: str,
    charge_repository: ChargeRepository = Depends(get_charge_repository),
) -> ChargeSchema:
    """Usado pelo storefront para dar polling no status da cobrança (ex:
    aguardando confirmação do Pix) — mesmo raciocínio sem-RBAC do endpoint
    acima."""
    try:
        charge = await GetChargeByOrder(charge_repository).execute(order_id)
    except ChargeNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _to_schema(charge)


@webhook_router.post("/mercado-pago")
async def mercado_pago_webhook(
    request: Request,
    charge_repository: ChargeRepository = Depends(get_charge_repository),
    order_repository: OrderRepository = Depends(get_order_repository),
    inventory_repository: InventoryRepository = Depends(get_inventory_repository),
    gateway: PaymentGateway = Depends(get_payment_gateway),
) -> dict[str, str]:
    """Recebe a notificação do Mercado Pago, valida a assinatura primeiro
    (nunca trata o payload como confiável antes disso), reconsulta o status
    real no gateway (ConfirmChargeFromWebhook nunca confia no payload) e,
    se a cobrança confirmou como paga, propaga para o pedido
    (MarkOrderPaid) — essa ponte cross-core só pode viver aqui (ADR-0002),
    nunca dentro de core-payments nem core-orders."""
    body = await request.body()
    query_params = dict(request.query_params)
    if not gateway.verify_webhook_signature(
        headers=dict(request.headers), query_params=query_params, body=body
    ):
        raise HTTPException(status_code=401, detail="Assinatura de webhook inválida")

    data_id = query_params.get("data.id", "")
    if not data_id:
        # O Mercado Pago manda outros tipos de notificação além de
        # pagamento (ex: "merchant_order") — sem data.id não há o que
        # confirmar aqui.
        return {"status": "ignored"}

    try:
        charge = await ConfirmChargeFromWebhook(gateway, charge_repository).execute(data_id)
    except ChargeNotFound:
        # Cobrança que não existe no nosso banco (ex: notificação de outro
        # ambiente/teste) — responde 200 mesmo assim, senão o Mercado Pago
        # reenvia indefinidamente algo que nunca vai passar a existir aqui.
        return {"status": "unknown_charge"}

    if charge.status.value == "paid":
        try:
            order = await GetOrder(order_repository).execute(charge.order_id)
            if order.payment_status == PaymentStatus.PENDING:
                paid_order = await MarkOrderPaid(order_repository).execute(charge.order_id)
                await fulfill_order_stock(paid_order, inventory_repository)
        except OrderNotFound:
            pass

    return {"status": "ok"}
