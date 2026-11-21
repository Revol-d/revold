"""Implementação Azure SQL da porta revold_payments.ports.ChargeRepository.
Espelha adapters/postgres/repository.py -- mesma lógica, só troca de onde o modelo vem."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from revold_payments.adapters.azure_sql.models import ChargeModel
from revold_payments.domain import Charge, ChargeStatus, Money, PaymentMethod


def _to_domain(model: ChargeModel) -> Charge:
    return Charge(
        charge_id=model.charge_id,
        order_id=model.order_id,
        provider=model.provider,
        provider_charge_id=model.provider_charge_id,
        method=PaymentMethod(model.method),
        amount=Money(model.amount_amount, model.amount_currency),
        status=ChargeStatus(model.status),
        pix_qr_code=model.pix_qr_code,
        pix_copy_paste=model.pix_copy_paste,
        checkout_url=model.checkout_url,
        created_at=model.created_at,
    )


class AzureSqlChargeRepository:
    """Implementa revold_payments.ports.ChargeRepository via SQLAlchemy async
    contra o Azure SQL Database."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, charge_id: str) -> Charge | None:
        model = await self._session.get(ChargeModel, charge_id)
        if model is None:
            return None
        return _to_domain(model)

    async def get_by_order(self, order_id: str) -> Charge | None:
        query = (
            select(ChargeModel)
            .where(ChargeModel.order_id == order_id)
            .order_by(ChargeModel.created_at.desc())
        )
        model = (await self._session.execute(query)).scalars().first()
        if model is None:
            return None
        return _to_domain(model)

    async def get_by_provider_charge_id(self, provider_charge_id: str) -> Charge | None:
        query = select(ChargeModel).where(
            ChargeModel.provider_charge_id == provider_charge_id
        )
        model = (await self._session.execute(query)).scalar_one_or_none()
        if model is None:
            return None
        return _to_domain(model)

    async def save(self, charge: Charge) -> None:
        model = await self._session.get(ChargeModel, charge.charge_id)
        if model is None:
            model = ChargeModel(charge_id=charge.charge_id)
            self._session.add(model)
        model.order_id = charge.order_id
        model.provider = charge.provider
        model.provider_charge_id = charge.provider_charge_id
        model.method = charge.method.value
        model.amount_amount = charge.amount.amount
        model.amount_currency = charge.amount.currency
        model.status = charge.status.value
        model.pix_qr_code = charge.pix_qr_code
        model.pix_copy_paste = charge.pix_copy_paste
        model.checkout_url = charge.checkout_url
        model.created_at = charge.created_at
        await self._session.commit()
