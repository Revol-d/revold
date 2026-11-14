"""Testes "sandbox" do adapter real do Mercado Pago — sem nenhuma
credencial nem chamada de rede de verdade. `respx` intercepta as chamadas
HTTP que o adapter faz via `httpx`, simulando os formatos de
request/response documentados publicamente pela API do Mercado Pago.

Diferente de Azurite (test_azure_blob_storage.py) ou aiosmtpd
(test_smtp_channel.py), não existe um emulador oficial do Mercado Pago
que fale o protocolo de verdade — então, diferente daqueles, isto não é
uma validação contra o protocolo real, só contra o formato documentado.
A próxima validação real só acontece com um `access_token` de teste, que
só o Samuel pode gerar (ver docstring de mercado_pago_gateway.py e
ADR-0024)."""
from __future__ import annotations

import hashlib
import hmac
from decimal import Decimal

import httpx
import pytest
import respx

from adapters_external.payments.mercado_pago_gateway import MercadoPagoGateway
from core_payments.domain import ChargeStatus, Money, PaymentMethod

_WEBHOOK_SECRET = "fake-webhook-secret-nao-e-real"


@pytest.fixture
def gateway() -> MercadoPagoGateway:
    return MercadoPagoGateway(
        access_token="fake-access-token-nao-e-real",
        webhook_secret=_WEBHOOK_SECRET,
        payer_email="loja@nickmoda.com.br",
    )


@respx.mock
async def test_create_charge_pix_monta_qr_code_a_partir_da_resposta(gateway: MercadoPagoGateway) -> None:
    route = respx.post("https://api.mercadopago.com/v1/payments").mock(
        return_value=httpx.Response(
            201,
            json={
                "id": 123456789,
                "status": "pending",
                "external_reference": "order-1",
                "point_of_interaction": {
                    "transaction_data": {
                        "qr_code": "00020126fake-copia-e-cola",
                        "qr_code_base64": "aWZha2VxcmNvZGU=",
                    }
                },
            },
        )
    )

    charge = await gateway.create_charge(
        order_id="order-1", amount=Money(Decimal("59.90")), method=PaymentMethod.PIX
    )

    assert route.called
    request_body = route.calls[0].request.content
    assert b'"payment_method_id":"pix"' in request_body or b"pix" in request_body
    assert charge.provider_charge_id == "123456789"
    assert charge.pix_copy_paste == "00020126fake-copia-e-cola"
    assert charge.pix_qr_code == "aWZha2VxcmNvZGU="
    assert charge.checkout_url is None


async def test_create_charge_cartao_nao_implementado(gateway: MercadoPagoGateway) -> None:
    with pytest.raises(NotImplementedError):
        await gateway.create_charge(
            order_id="order-1", amount=Money(Decimal("59.90")), method=PaymentMethod.CREDIT_CARD
        )


@respx.mock
@pytest.mark.parametrize(
    "mp_status,expected",
    [
        ("approved", ChargeStatus.PAID),
        ("pending", ChargeStatus.PENDING),
        ("in_process", ChargeStatus.PENDING),
        ("rejected", ChargeStatus.FAILED),
        ("cancelled", ChargeStatus.FAILED),
        ("refunded", ChargeStatus.REFUNDED),
    ],
)
async def test_get_charge_status_mapeia_status_do_mercado_pago(
    gateway: MercadoPagoGateway, mp_status: str, expected: ChargeStatus
) -> None:
    respx.get("https://api.mercadopago.com/v1/payments/123456789").mock(
        return_value=httpx.Response(200, json={"id": 123456789, "status": mp_status})
    )
    status = await gateway.get_charge_status("123456789")
    assert status == expected


def _sign(*, data_id: str, request_id: str, ts: str, secret: str) -> str:
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    digest = hmac.new(secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"ts={ts},v1={digest}"


def test_verify_webhook_signature_valida_assinatura_correta(gateway: MercadoPagoGateway) -> None:
    signature = _sign(data_id="123456789", request_id="req-1", ts="1700000000", secret=_WEBHOOK_SECRET)
    assert gateway.verify_webhook_signature(
        headers={"x-signature": signature, "x-request-id": "req-1"},
        query_params={"data.id": "123456789"},
        body=b"{}",
    )


def test_verify_webhook_signature_rejeita_assinatura_forjada(gateway: MercadoPagoGateway) -> None:
    signature = _sign(data_id="123456789", request_id="req-1", ts="1700000000", secret="segredo-errado")
    assert not gateway.verify_webhook_signature(
        headers={"x-signature": signature, "x-request-id": "req-1"},
        query_params={"data.id": "123456789"},
        body=b"{}",
    )


def test_verify_webhook_signature_rejeita_campos_ausentes(gateway: MercadoPagoGateway) -> None:
    assert not gateway.verify_webhook_signature(headers={}, query_params={}, body=b"{}")
