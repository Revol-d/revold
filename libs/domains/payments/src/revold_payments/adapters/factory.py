"""Monta a implementação de ChargeRepository contra o Azure SQL Database. Mesmo
padrão de revold_store_settings.adapters.factory. Postgres foi removido (Fase 7 do
plano de migração Postgres -> Azure SQL, docs internos).

Não confundir com revold_payments.adapters.gateways.factory.build_payment_gateway,
que seleciona PaymentGateway (fake/mercado_pago via PAYMENT_PROVIDER) -- são duas
portas e duas fábricas independentes do mesmo domínio.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_payments.adapters.azure_sql.repository import AzureSqlChargeRepository
from revold_payments.ports import ChargeRepository


def build_charge_repository(session: AsyncSession) -> ChargeRepository:
    return AzureSqlChargeRepository(session)
