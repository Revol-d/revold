"""Seleciona a implementação de PaymentGateway a partir de
PAYMENT_PROVIDER. Mesmo padrão de adapters_external.media.factory /
adapters_external.notification.factory (ADR-0024).
"""
from __future__ import annotations

import os

from core_payments.ports import PaymentGateway

from adapters_external.payments.fake_gateway import FakePaymentGateway


def get_payment_gateway() -> PaymentGateway:
    provider = os.environ.get("PAYMENT_PROVIDER", "fake")
    if provider == "fake":
        return FakePaymentGateway()
    if provider == "mercado_pago":
        from adapters_external.payments.mercado_pago_gateway import MercadoPagoGateway

        access_token = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
        webhook_secret = os.environ.get("MERCADO_PAGO_WEBHOOK_SECRET")
        payer_email = os.environ.get("MERCADO_PAGO_PAYER_EMAIL")
        if not access_token or not webhook_secret or not payer_email:
            raise NotImplementedError(
                "PAYMENT_PROVIDER=mercado_pago requer MERCADO_PAGO_ACCESS_TOKEN, "
                "MERCADO_PAGO_WEBHOOK_SECRET e MERCADO_PAGO_PAYER_EMAIL configurados "
                "(ver .env.example e ADR-0024)."
            )
        return MercadoPagoGateway(
            access_token=access_token, webhook_secret=webhook_secret, payer_email=payer_email
        )
    raise ValueError(f"PAYMENT_PROVIDER desconhecido: {provider!r}")
