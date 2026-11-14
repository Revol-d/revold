"""Router HTTP do core-cart. Fino: só traduz HTTP <-> caso de uso.

O endpoint de checkout também é responsabilidade desta camada mapear
core_cart.domain.Cart -> core_communication.domain.CartSummary — os dois
cores não se importam entre si (ADR-0002), então essa tradução é
orquestração, e orquestração vive no api-gateway (ou num orchestrator
dedicado, quando um existir). Pela mesma razão, a reserva de estoque
(core-inventory) no momento do checkout também é orquestrada aqui.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from api_gateway.dependencies import (
    get_cart_repository,
    get_checkout_handoff,
    get_event_publisher,
    get_inventory_repository,
    get_low_stock_threshold,
    get_metrics_publisher,
    get_order_repository,
)
from api_gateway.orchestration import notify_if_low_stock
from core_cart.domain import Cart, CartItemNotFound, EmptyCart
from core_cart.ports import CartRepository
from core_cart.schemas import (
    AddItemRequestSchema,
    CartItemSchema,
    CartSchema,
    CheckoutHandoffResponseSchema,
    UpdateQuantityRequestSchema,
)
from core_cart.use_cases import (
    AddItem,
    ClearCart,
    GetCartForCheckout,
    GetOrCreateCart,
    RemoveItem,
    UpdateItemQuantity,
)
from core_communication.domain import CartSummary, CartSummaryLine
from core_communication.ports import CheckoutHandoff
from core_events.domain import DomainEvent
from core_events.ports import EventPublisher
from core_inventory.domain import InsufficientStock, StockLevelNotFound
from core_inventory.ports import InventoryRepository
from core_inventory.use_cases import GetStockLevel, ReleaseStock, ReserveStock
from core_observability.ports import MetricsPublisher
from core_orders.domain import Money as OrderMoney
from core_orders.domain import OrderLine
from core_orders.ports import OrderRepository
from core_orders.use_cases import CreateOrder

router = APIRouter(prefix="/api/cart", tags=["cart"])


async def _available_quantity(sku: str, inventory_repository: InventoryRepository) -> int | None:
    """Consulta informativa de estoque — nunca bloqueia, só documenta na
    resposta quanto há disponível. SKU sem StockLevel cadastrado (ainda não
    rastreado) retorna None."""
    try:
        stock = await GetStockLevel(inventory_repository).execute(sku)
    except StockLevelNotFound:
        return None
    return stock.quantity_available


async def _cart_to_schema(cart: Cart, inventory_repository: InventoryRepository) -> CartSchema:
    items = [
        CartItemSchema(
            sku=i.sku,
            name=i.name,
            variant_label=i.variant_label,
            unit_price=i.unit_price.amount,
            quantity=i.quantity,
            available_quantity=await _available_quantity(i.sku, inventory_repository),
        )
        for i in cart.items
    ]
    return CartSchema(
        cart_id=cart.cart_id,
        items=items,
        total=cart.total().amount,
        currency=cart.currency,
    )


def _cart_to_summary(cart: Cart) -> CartSummary:
    return CartSummary(
        lines=tuple(
            CartSummaryLine(
                product_name=i.name,
                variant_label=i.variant_label,
                quantity=i.quantity,
                unit_price_amount=str(i.unit_price.amount),
            )
            for i in cart.items
        ),
        total_amount=str(cart.total().amount),
        currency=cart.currency,
    )


def _cart_to_order_lines(cart: Cart) -> list[OrderLine]:
    """Traduz Cart (core_cart) -> OrderLine (core_orders) — os dois cores
    não se importam entre si (ADR-0002), essa tradução é orquestração e
    vive aqui, mesmo raciocínio de _cart_to_summary logo acima."""
    return [
        OrderLine(
            sku=item.sku,
            product_name=item.name,
            variant_label=item.variant_label,
            unit_price=OrderMoney(item.unit_price.amount, item.unit_price.currency),
            quantity=item.quantity,
        )
        for item in cart.items
    ]


def _summary_to_text(summary: CartSummary) -> str:
    lines = [
        f"{line.quantity}x {line.product_name} ({line.variant_label})" for line in summary.lines
    ]
    return f"{', '.join(lines)} — total {summary.total_amount} {summary.currency}"


@router.get("/{cart_id}", response_model=CartSchema)
async def get_cart(
    cart_id: str,
    repository: CartRepository = Depends(get_cart_repository),
    inventory_repository: InventoryRepository = Depends(get_inventory_repository),
) -> CartSchema:
    cart = await GetOrCreateCart(repository).execute(cart_id)
    return await _cart_to_schema(cart, inventory_repository)


@router.delete("/{cart_id}", status_code=204)
async def clear_cart(
    cart_id: str, repository: CartRepository = Depends(get_cart_repository)
) -> Response:
    await ClearCart(repository).execute(cart_id)
    return Response(status_code=204)


@router.post("/{cart_id}/items", response_model=CartSchema)
async def add_item(
    cart_id: str,
    body: AddItemRequestSchema,
    repository: CartRepository = Depends(get_cart_repository),
    inventory_repository: InventoryRepository = Depends(get_inventory_repository),
) -> CartSchema:
    cart = await AddItem(repository).execute(
        cart_id,
        sku=body.sku,
        name=body.name,
        variant_label=body.variant_label,
        unit_price_amount=str(body.unit_price),
        quantity=body.quantity,
    )
    return await _cart_to_schema(cart, inventory_repository)


@router.patch("/{cart_id}/items/{sku}", response_model=CartSchema)
async def update_item_quantity(
    cart_id: str,
    sku: str,
    body: UpdateQuantityRequestSchema,
    repository: CartRepository = Depends(get_cart_repository),
    inventory_repository: InventoryRepository = Depends(get_inventory_repository),
) -> CartSchema:
    try:
        cart = await UpdateItemQuantity(repository).execute(cart_id, sku, body.quantity)
    except CartItemNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await _cart_to_schema(cart, inventory_repository)


@router.delete("/{cart_id}/items/{sku}", response_model=CartSchema)
async def remove_item(
    cart_id: str,
    sku: str,
    repository: CartRepository = Depends(get_cart_repository),
    inventory_repository: InventoryRepository = Depends(get_inventory_repository),
) -> CartSchema:
    try:
        cart = await RemoveItem(repository).execute(cart_id, sku)
    except CartItemNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return await _cart_to_schema(cart, inventory_repository)


async def _reserve_cart_stock(
    cart: Cart,
    inventory_repository: InventoryRepository,
    event_publisher: EventPublisher,
    low_stock_threshold: int,
    metrics: MetricsPublisher | None = None,
) -> None:
    """Reserva (não baixa) o estoque de cada item do carrinho antes do handoff
    de checkout (ADR-0005: a baixa definitiva só acontece quando a venda é
    confirmada manualmente pelo WhatsApp — ver core_inventory.use_cases).

    Um SKU sem StockLevel cadastrado é tratado como "ainda não rastreado" e
    não bloqueia o checkout — core-inventory está sendo adotado
    gradualmente, nem todo produto do catálogo tem estoque cadastrado ainda.

    Como cada reserva é commitada de forma independente (não há uma única
    transação cobrindo o carrinho inteiro), se um item no meio da lista
    falhar por falta de estoque, as reservas já feitas para os itens
    anteriores são desfeitas explicitamente antes de propagar o erro.
    """
    reserved: list[tuple[str, int]] = []
    try:
        for item in cart.items:
            try:
                stock = await ReserveStock(inventory_repository).execute(item.sku, item.quantity)
            except StockLevelNotFound:
                continue
            reserved.append((item.sku, item.quantity))
            await notify_if_low_stock(stock, event_publisher, low_stock_threshold, metrics)
    except InsufficientStock:
        for sku, quantity in reserved:
            await ReleaseStock(inventory_repository).execute(sku, quantity)
        raise


@router.post("/{cart_id}/checkout", response_model=CheckoutHandoffResponseSchema)
async def start_checkout(
    cart_id: str,
    repository: CartRepository = Depends(get_cart_repository),
    inventory_repository: InventoryRepository = Depends(get_inventory_repository),
    checkout: CheckoutHandoff = Depends(get_checkout_handoff),
    event_publisher: EventPublisher = Depends(get_event_publisher),
    low_stock_threshold: int = Depends(get_low_stock_threshold),
    metrics: MetricsPublisher = Depends(get_metrics_publisher),
    order_repository: OrderRepository = Depends(get_order_repository),
) -> CheckoutHandoffResponseSchema:
    try:
        cart = await GetCartForCheckout(repository).execute(cart_id)
    except EmptyCart as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        await _reserve_cart_stock(
            cart, inventory_repository, event_publisher, low_stock_threshold, metrics
        )
    except InsufficientStock as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    summary = _cart_to_summary(cart)
    try:
        url = checkout.build_handoff(summary)
    except ValueError as exc:
        # o estoque já reservado não deve ficar preso se o handoff falhar
        # (ex.: NICK_WHATSAPP_NUMBER não configurado) — libera antes de propagar.
        for item in cart.items:
            try:
                await ReleaseStock(inventory_repository).execute(item.sku, item.quantity)
            except StockLevelNotFound:
                continue
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Registra o pedido (ADR-0023) — até aqui o checkout era efêmero: virava
    # um link do WhatsApp e nada ficava gravado do lado do Nick. O pedido é
    # criado depois que o handoff é montado com sucesso (estoque já
    # reservado de verdade) para não registrar uma tentativa que nunca
    # chegou a sair do carrinho.
    order = await CreateOrder(order_repository).execute(
        cart_id=cart_id, lines=_cart_to_order_lines(cart), currency=cart.currency
    )

    # Avisa a Nick que um carrinho entrou em checkout — o handoff em si (o
    # link do WhatsApp) ainda depende do cliente abrir e mandar a mensagem;
    # este evento é o que faz a Nick saber que precisa ficar de olho. Quem
    # de fato notifica roda assíncrono (ver
    # workers/event_worker.dispatch.handle_checkout_created, ADR-0013) —
    # se o canal de notificação falhar, isso não deve derrubar o checkout,
    # que já reservou estoque de verdade.
    await event_publisher.publish(
        DomainEvent(
            name="checkout.created",
            payload={
                "cart_id": cart_id,
                "order_id": order.order_id,
                "summary_text": _summary_to_text(summary),
            },
        )
    )
    metrics.increment("checkout_created_total")

    return CheckoutHandoffResponseSchema(
        handoff_url=url, provider=checkout.provider_name, order_id=order.order_id
    )
