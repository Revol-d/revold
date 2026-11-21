"""Seleciona a implementação de ChargeRepository pelo nome do provedor de
persistência. Mesmo padrão de revold_store_settings.adapters.factory.

Não confundir com revold_payments.adapters.gateways.factory.build_payment_gateway,
que seleciona PaymentGateway (fake/mercado_pago via PAYMENT_PROVIDER) -- são duas
portas e duas fábricas independentes do mesmo domínio.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from revold_payments.ports import ChargeRepository

DEFAULT_PERSISTENCE_PROVIDER = "postgres"


def build_charge_repository(
    session: AsyncSession, provider: str = DEFAULT_PERSISTENCE_PROVIDER
) -> ChargeRepository:
    if provider == "postgres":
        from revold_payments.adapters.postgres.repository import PostgresChargeRepository

        return PostgresChargeRepository(session)
    if provider == "azure-sql":
        from revold_payments.adapters.azure_sql.repository import AzureSqlChargeRepository

        return AzureSqlChargeRepository(session)
    raise ValueError(f"PERSISTENCE_PROVIDER desconhecido: {provider!r}")
