"""Adapter dev/teste de core_payments.ports.PaymentGateway — não fala com
nenhum serviço externo. Aprova automaticamente depois de N consultas de
status (configurável), para simular o atraso real de confirmação de Pix
sem precisar de nada externo.
"""
from __future__ import annotations

import itertools
import uuid
from typing import Mapping

from core_payments.domain import Charge, ChargeStatus, Money, PaymentMethod


class FakePaymentGateway:
    provider_name = "fake"

    def __init__(self, *, approve_after_polls: int = 0) -> None:
        """approve_after_polls=0 aprova na primeira consulta de status
        (útil pro fluxo feliz); um valor maior simula "ainda pendente" por
        algumas consultas antes de aprovar — para exercitar o caminho de
        polling sem precisar de tempo real passando."""
        self._approve_after_polls = approve_after_polls
        self._poll_counts: dict[str, int] = {}
        self._id_counter = itertools.count(1)

    async def create_charge(self, *, order_id: str, amount: Money, method: PaymentMethod) -> Charge:
        provider_charge_id = f"fake-{next(self._id_counter)}-{uuid.uuid4().hex[:8]}"
        return Charge(
            charge_id="",
            order_id=order_id,
            provider=self.provider_name,
            provider_charge_id=provider_charge_id,
            method=method,
            amount=amount,
            pix_qr_code=f"00020126fake-qr-{provider_charge_id}" if method == PaymentMethod.PIX else None,
            pix_copy_paste=(
                f"00020126fake-copia-cola-{provider_charge_id}" if method == PaymentMethod.PIX else None
            ),
            checkout_url=(
                f"https://checkout.fake.test/{provider_charge_id}"
                if method == PaymentMethod.CREDIT_CARD
                else None
            ),
        )

    async def get_charge_status(self, provider_charge_id: str) -> ChargeStatus:
        count = self._poll_counts.get(provider_charge_id, 0) + 1
        self._poll_counts[provider_charge_id] = count
        if count > self._approve_after_polls:
            return ChargeStatus.PAID
        return ChargeStatus.PENDING

    def verify_webhook_signature(
        self, *, headers: Mapping[str, str], query_params: Mapping[str, str], body: bytes
    ) -> bool:
        # Dev: qualquer assinatura não vazia é aceita — não há segredo
        # nenhum configurado localmente.
        return bool(headers.get("x-signature"))
