"""Portas (interfaces) que `payments` espera que a infraestrutura
implemente. Nenhum adapter concreto (Mercado Pago, fake) é conhecido aqui
— `payments` nunca importa httpx nem SQLAlchemy.
"""
from __future__ import annotations

from typing import Mapping, Protocol

from revold_payments.domain import Charge, ChargeStatus, Money, PaymentMethod


class PaymentGateway(Protocol):
    provider_name: str

    async def create_charge(
        self, *, order_id: str, amount: Money, method: PaymentMethod
    ) -> Charge:
        """Abre uma cobrança no gateway e devolve a Charge já com
        provider_charge_id e (quando Pix) qr_code/copy_paste, ou (quando
        cartão) checkout_url preenchidos."""
        ...

    async def get_charge_status(self, provider_charge_id: str) -> ChargeStatus:
        """Consulta o status atual no gateway — usado tanto por polling
        quanto para confirmar o conteúdo de um webhook (nunca confiar cegamente
        no payload do webhook, sempre reconsultar o gateway)."""
        ...

    def verify_webhook_signature(
        self, *, headers: Mapping[str, str], query_params: Mapping[str, str], body: bytes
    ) -> bool:
        """Valida a assinatura do webhook recebido — só depois disso o
        payload é tratado como confiável. Recebe headers/query params/corpo
        crus porque cada gateway assina um conjunto diferente de campos
        (o Mercado Pago, por exemplo, assina um manifesto que inclui um
        campo da query string, não só do corpo)."""
        ...


class ChargeRepository(Protocol):
    async def get(self, charge_id: str) -> Charge | None: ...

    async def get_by_order(self, order_id: str) -> Charge | None:
        """Um pedido tem no máximo uma cobrança ativa por vez nesta onda
        (retentativa de pagamento não está no escopo — ver ADR-0024)."""
        ...

    async def get_by_provider_charge_id(self, provider_charge_id: str) -> Charge | None:
        """É assim que um webhook (que só carrega o id do gateway) encontra
        a cobrança correspondente aqui dentro."""
        ...

    async def save(self, charge: Charge) -> None:
        """Cria ou atualiza uma cobrança por completo (upsert por charge_id)."""
        ...
