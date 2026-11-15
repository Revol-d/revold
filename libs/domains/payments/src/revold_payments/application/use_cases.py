"""Casos de uso do `payments` (ADR-0024)."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from revold_payments.domain import Charge, ChargeNotFound, ChargeStatus, Money, PaymentMethod
from revold_payments.ports import ChargeRepository, PaymentGateway


class CreateCharge:
    """Abre uma cobrança nova para um pedido. Não sabe nada de `orders`
    — quem chama (api-gateway) já traduziu Order -> (order_id, amount)."""

    def __init__(self, gateway: PaymentGateway, repository: ChargeRepository) -> None:
        self._gateway = gateway
        self._repository = repository

    async def execute(self, *, order_id: str, amount: Money, method: PaymentMethod) -> Charge:
        existing = await self._repository.get_by_order(order_id)
        if existing is not None and existing.status == ChargeStatus.PENDING:
            # Reaproveita a cobrança em aberto em vez de abrir uma segunda
            # no gateway — evita cobrança duplicada se o cliente clicar
            # "pagar" duas vezes antes do primeiro Pix expirar.
            return existing

        charge = await self._gateway.create_charge(order_id=order_id, amount=amount, method=method)
        charge.charge_id = charge.charge_id or uuid.uuid4().hex
        if not charge.created_at:
            charge.created_at = datetime.now(UTC).isoformat()
        await self._repository.save(charge)
        return charge


class GetCharge:
    def __init__(self, repository: ChargeRepository) -> None:
        self._repository = repository

    async def execute(self, charge_id: str) -> Charge:
        charge = await self._repository.get(charge_id)
        if charge is None:
            raise ChargeNotFound(charge_id)
        return charge


class GetChargeByOrder:
    def __init__(self, repository: ChargeRepository) -> None:
        self._repository = repository

    async def execute(self, order_id: str) -> Charge:
        charge = await self._repository.get_by_order(order_id)
        if charge is None:
            raise ChargeNotFound(order_id)
        return charge


class ConfirmChargeFromWebhook:
    """Chamado depois que o api-gateway já validou a assinatura do webhook
    (`PaymentGateway.verify_webhook_signature`) — nunca confia no status que
    o payload do webhook alega, sempre reconsulta o gateway
    (`get_charge_status`) antes de mudar o estado local."""

    def __init__(self, gateway: PaymentGateway, repository: ChargeRepository) -> None:
        self._gateway = gateway
        self._repository = repository

    async def execute(self, provider_charge_id: str) -> Charge:
        charge = await self._repository.get_by_provider_charge_id(provider_charge_id)
        if charge is None:
            raise ChargeNotFound(provider_charge_id)

        if charge.status != ChargeStatus.PENDING:
            # Webhook duplicado (o gateway pode reenviar) — idempotente,
            # não é erro.
            return charge

        status = await self._gateway.get_charge_status(provider_charge_id)
        if status == ChargeStatus.PAID:
            charge.mark_paid()
        elif status == ChargeStatus.EXPIRED:
            charge.mark_expired()
        elif status == ChargeStatus.FAILED:
            charge.mark_failed()
        # PENDING no gateway ainda -> nada muda aqui.

        await self._repository.save(charge)
        return charge
