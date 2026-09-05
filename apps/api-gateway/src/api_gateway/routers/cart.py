"""Router HTTP do core-cart. Fino: só traduz HTTP <-> caso de uso.

O endpoint de checkout também é responsabilidade desta camada mapear
core_cart.domain.Cart -> core_communication.domain.CartSummary — os dois
cores não se importam entre si (ADR-0002), então essa tradução é
orquestração, e orquestração vive no api-gateway (ou num orchestrator
dedicado, quando um existir).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from api_gateway.dependencies import get_cart_repository, get_checkout_handoff
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

router = APIRouter(prefix="/api/cart", tags=["cart"])


def _cart_to_schema(cart: Cart) -> CartSchema:
    return CartSchema(
        cart_id=cart.cart_id,
        items=[
            CartItemSchema(
                sku=i.sku,
                name=i.name,
                variant_label=i.variant_label,
                unit_price=i.unit_price.amount,
                quantity=i.quantity,
            )
            for i in cart.items
        ],
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


@router.get("/{cart_id}", response_model=CartSchema)
async def get_cart(
    cart_id: str, repository: CartRepository = Depends(get_cart_repository)
) -> CartSchema:
    cart = await GetOrCreateCart(repository).execute(cart_id)
    return _cart_to_schema(cart)


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
) -> CartSchema:
    cart = await AddItem(repository).execute(
        cart_id,
        sku=body.sku,
        name=body.name,
        variant_label=body.variant_label,
        unit_price_amount=str(body.unit_price),
        quantity=body.quantity,
    )
    return _cart_to_schema(cart)


@router.patch("/{cart_id}/items/{sku}", response_model=CartSchema)
async def update_item_quantity(
    cart_id: str,
    sku: str,
    body: UpdateQuantityRequestSchema,
    repository: CartRepository = Depends(get_cart_repository),
) -> CartSchema:
    try:
        cart = await UpdateItemQuantity(repository).execute(cart_id, sku, body.quantity)
    except CartItemNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _cart_to_schema(cart)


@router.delete("/{cart_id}/items/{sku}", response_model=CartSchema)
async def remove_item(
    cart_id: str, sku: str, repository: CartRepository = Depends(get_cart_repository)
) -> CartSchema:
    try:
        cart = await RemoveItem(repository).execute(cart_id, sku)
    except CartItemNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _cart_to_schema(cart)


@router.post("/{cart_id}/checkout", response_model=CheckoutHandoffResponseSchema)
async def start_checkout(
    cart_id: str,
    repository: CartRepository = Depends(get_cart_repository),
    checkout: CheckoutHandoff = Depends(get_checkout_handoff),
) -> CheckoutHandoffResponseSchema:
    try:
        cart = await GetCartForCheckout(repository).execute(cart_id)
    except EmptyCart as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        url = checkout.build_handoff(_cart_to_summary(cart))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CheckoutHandoffResponseSchema(handoff_url=url, provider=checkout.provider_name)
