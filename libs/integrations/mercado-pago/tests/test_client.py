"""O cliente do Mercado Pago em sandbox HTTP (respx): formato do request, sem conta real."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from revold_mercado_pago.client import MercadoPagoClient

_PAYMENTS = "https://api.mercadopago.com/v1/payments"


@pytest.fixture
def client() -> MercadoPagoClient:
    return MercadoPagoClient(access_token="fake-access-token-nao-e-real")


@respx.mock
async def test_create_pix_payment_sends_the_documented_body(client: MercadoPagoClient) -> None:
    route = respx.post(_PAYMENTS).mock(
        return_value=httpx.Response(201, json={"id": 123456789, "status": "pending"})
    )

    data = await client.create_pix_payment(
        amount=59.9,
        description="Pedido order-1",
        payer_email="loja@example.com",
        external_reference="order-1",
    )

    assert data == {"id": 123456789, "status": "pending"}
    request = route.calls[0].request
    assert request.headers["Authorization"] == "Bearer fake-access-token-nao-e-real"
    assert request.headers["X-Idempotency-Key"]
    assert json.loads(request.content) == {
        "transaction_amount": 59.9,
        "description": "Pedido order-1",
        "payment_method_id": "pix",
        "payer": {"email": "loja@example.com"},
        "external_reference": "order-1",
    }


@respx.mock
async def test_each_write_gets_its_own_idempotency_key(client: MercadoPagoClient) -> None:
    route = respx.post(_PAYMENTS).mock(return_value=httpx.Response(201, json={"id": 1}))

    for _ in range(2):
        await client.create_pix_payment(
            amount=1.0, description="d", payer_email="loja@example.com", external_reference="o"
        )

    keys = [call.request.headers["X-Idempotency-Key"] for call in route.calls]
    assert keys[0] != keys[1]


@respx.mock
async def test_get_payment_returns_the_response(client: MercadoPagoClient) -> None:
    respx.get(f"{_PAYMENTS}/123456789").mock(
        return_value=httpx.Response(200, json={"id": 123456789, "status": "approved"})
    )

    assert (await client.get_payment("123456789"))["status"] == "approved"


@respx.mock
async def test_api_error_is_raised_not_swallowed(client: MercadoPagoClient) -> None:
    respx.get(f"{_PAYMENTS}/404").mock(
        return_value=httpx.Response(404, json={"message": "not found"})
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_payment("404")
