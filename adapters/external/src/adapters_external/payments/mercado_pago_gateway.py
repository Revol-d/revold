"""Adapter real de core_payments.ports.PaymentGateway — Mercado Pago
(ADR-0024).

**Escopo desta onda: só Pix.** Cartão via Mercado Pago tem duas rotas
possíveis (Checkout Pro com redirecionamento, ou Payment Brick com
tokenização client-side) e as duas exigem uma peça de frontend que ainda
não foi desenhada — incluindo a decisão pendente com o Samuel sobre
parcelamento (ver claude/planejamento-pagamentos-e-comunicacao-avancada.md).
Implementar cartão agora, sem essa peça, arriscaria uma reconciliação de
webhook incoerente (o id que se guardaria na criação da cobrança não seria
o mesmo id que o webhook manda de volta). `create_charge` com
`PaymentMethod.CREDIT_CARD` levanta `NotImplementedError` de propósito até
essa decisão existir — mesmo padrão de `core_identity` para Azure
AD/Google (ADR-0003): a porta já suporta, o adapter real ainda não.

Pix é uma cobrança direta: `POST /v1/payments` com
`payment_method_id="pix"` devolve o id do pagamento imediatamente, junto
com QR code e "copia e cola" — o mesmo id volta no webhook, então a
reconciliação é direta (sem a ambiguidade preferência-vs-pagamento do
Checkout Pro).

**Validação desta onda**: sandbox via `respx` (ver
adapters/external/tests/test_mercado_pago_gateway.py), simulando os
formatos de request/response documentados publicamente pela API do
Mercado Pago — não uma conta de sandbox real (diferente de
Azurite/aiosmtpd, que são o protocolo real rodando localmente, não existe
emulador oficial equivalente do Mercado Pago). Criar uma conta, mesmo de
teste, exige um cadastro que só o Samuel pode fazer — quando ele tiver um
`access_token` de teste, a próxima validação é rodar contra ele de
verdade.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import Mapping

import httpx

from core_payments.domain import Charge, ChargeStatus, Money, PaymentMethod

_API_BASE = "https://api.mercadopago.com"

_STATUS_MAP = {
    "approved": ChargeStatus.PAID,
    "pending": ChargeStatus.PENDING,
    "in_process": ChargeStatus.PENDING,
    "authorized": ChargeStatus.PENDING,
    "rejected": ChargeStatus.FAILED,
    "cancelled": ChargeStatus.FAILED,
    "refunded": ChargeStatus.REFUNDED,
    "charged_back": ChargeStatus.REFUNDED,
}


class MercadoPagoGateway:
    provider_name = "mercado_pago"

    def __init__(self, *, access_token: str, webhook_secret: str, payer_email: str) -> None:
        self._access_token = access_token
        self._webhook_secret = webhook_secret
        # Mercado Pago exige um e-mail de pagador em todo POST /v1/payments
        # — usamos um e-mail fixo da própria loja enquanto o checkout não
        # coleta e-mail do cliente antes do pagamento (mesmo ponto em
        # aberto do checkout via WhatsApp, ADR-0005).
        self._payer_email = payer_email

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": uuid.uuid4().hex,
        }

    async def create_charge(self, *, order_id: str, amount: Money, method: PaymentMethod) -> Charge:
        if method != PaymentMethod.PIX:
            raise NotImplementedError(
                "MercadoPagoGateway só implementa Pix nesta onda — ver docstring do módulo "
                "para o motivo (cartão depende de uma decisão de UI ainda pendente)."
            )

        body = {
            "transaction_amount": float(amount.amount),
            "description": f"Pedido {order_id}",
            "payment_method_id": "pix",
            "payer": {"email": self._payer_email},
            "external_reference": order_id,
        }
        async with httpx.AsyncClient(base_url=_API_BASE, timeout=15.0) as client:
            response = await client.post("/v1/payments", json=body, headers=self._headers())
            response.raise_for_status()
            data = response.json()

        transaction_data = data.get("point_of_interaction", {}).get("transaction_data", {})
        return Charge(
            charge_id="",
            order_id=order_id,
            provider=self.provider_name,
            provider_charge_id=str(data["id"]),
            method=method,
            amount=amount,
            pix_qr_code=transaction_data.get("qr_code_base64"),
            pix_copy_paste=transaction_data.get("qr_code"),
        )

    async def get_charge_status(self, provider_charge_id: str) -> ChargeStatus:
        async with httpx.AsyncClient(base_url=_API_BASE, timeout=15.0) as client:
            response = await client.get(
                f"/v1/payments/{provider_charge_id}",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            response.raise_for_status()
            data = response.json()
        return _STATUS_MAP.get(data.get("status", ""), ChargeStatus.PENDING)

    def verify_webhook_signature(
        self, *, headers: Mapping[str, str], query_params: Mapping[str, str], body: bytes
    ) -> bool:
        """Esquema de assinatura documentado do Mercado Pago (webhooks v2):
        o cabeçalho `x-signature` carrega `ts=<epoch>,v1=<hmac-hex>`; o
        manifesto assinado é `id:<data.id>;request-id:<x-request-id>;ts:<ts>;`
        (HMAC-SHA256 com o segredo do webhook configurado na conta) — não
        assina o corpo da requisição, só esses três campos."""
        signature_header = headers.get("x-signature", "")
        request_id = headers.get("x-request-id", "")
        data_id = query_params.get("data.id", "")
        if not signature_header or not request_id or not data_id:
            return False

        parts = dict(
            item.split("=", 1) for item in signature_header.split(",") if "=" in item
        )
        ts = parts.get("ts")
        received_v1 = parts.get("v1")
        if not ts or not received_v1:
            return False

        manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
        expected = hmac.new(
            self._webhook_secret.encode("utf-8"), manifest.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, received_v1)
