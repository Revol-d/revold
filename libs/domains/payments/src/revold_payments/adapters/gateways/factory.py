"""Seleciona a implementação de PaymentGateway a partir de `PaymentSettings` (ADR-0024).

Este módulo não lê o ambiente. O `settings.py` do app lê e entrega um `PaymentSettings` pronto
(em geral via `PaymentSettings.from_mapping(env_snapshot())`). Os nomes das chaves são os do
`.env.example`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from revold_payments.adapters.gateways.fake_gateway import FakePaymentGateway
from revold_payments.ports import PaymentGateway


@dataclass(frozen=True)
class PaymentSettings:
    """Configuração do gateway de pagamento. Segredo fica fora do `repr`."""

    provider: str = "fake"
    mercado_pago_access_token: str | None = field(default=None, repr=False)
    mercado_pago_webhook_secret: str | None = field(default=None, repr=False)
    mercado_pago_payer_email: str | None = None

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> PaymentSettings:
        """Monta a configuração a partir de um mapeamento com as chaves do `.env.example`."""
        return cls(
            provider=values.get("PAYMENT_PROVIDER", "fake"),
            mercado_pago_access_token=values.get("MERCADO_PAGO_ACCESS_TOKEN"),
            mercado_pago_webhook_secret=values.get("MERCADO_PAGO_WEBHOOK_SECRET"),
            mercado_pago_payer_email=values.get("MERCADO_PAGO_PAYER_EMAIL"),
        )


def build_payment_gateway(settings: PaymentSettings | None = None) -> PaymentGateway:
    settings = settings or PaymentSettings()
    provider = settings.provider
    if provider == "fake":
        return FakePaymentGateway()
    if provider == "mercado_pago":
        from revold_payments.adapters.gateways.mercado_pago_gateway import MercadoPagoGateway

        if not (
            settings.mercado_pago_access_token
            and settings.mercado_pago_webhook_secret
            and settings.mercado_pago_payer_email
        ):
            raise NotImplementedError(
                "PAYMENT_PROVIDER=mercado_pago requer MERCADO_PAGO_ACCESS_TOKEN, "
                "MERCADO_PAGO_WEBHOOK_SECRET e MERCADO_PAGO_PAYER_EMAIL configurados "
                "(ver .env.example e ADR-0024)."
            )
        return MercadoPagoGateway(
            access_token=settings.mercado_pago_access_token,
            webhook_secret=settings.mercado_pago_webhook_secret,
            payer_email=settings.mercado_pago_payer_email,
        )
    raise ValueError(f"PAYMENT_PROVIDER desconhecido: {provider!r}")
