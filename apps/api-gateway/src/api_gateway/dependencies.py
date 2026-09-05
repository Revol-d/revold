"""Injeção de dependência do api-gateway.

O api-gateway é a única camada que conhece FastAPI + a implementação
concreta dos adapters. Os cores nunca são importados fora daqui a não ser
pelas suas portas e casos de uso.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from adapters_external.checkout.whatsapp_clicktochat import WhatsAppClickToChatCheckout
from adapters_persistence.cart.redis_repository import RedisCartRepository
from adapters_persistence.catalog.repository import PostgresProductRepository
from adapters_persistence.db import make_engine, make_session_factory
from adapters_persistence.redis_client import make_redis_client
from core_cart.ports import CartRepository
from core_catalog.ports import ProductRepository
from core_communication.ports import CheckoutHandoff

_engine = make_engine()
_session_factory = make_session_factory(_engine)
_redis_client = make_redis_client()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with _session_factory() as session:
        yield session


async def get_product_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ProductRepository:
    return PostgresProductRepository(session)


def get_redis_client() -> Redis:
    return _redis_client


async def get_cart_repository(
    redis: Redis = Depends(get_redis_client),
) -> CartRepository:
    return RedisCartRepository(redis)


def get_checkout_handoff() -> CheckoutHandoff:
    # Única implementação hoje é o clique-para-conversar do WhatsApp
    # (ADR-0005). Trocar para a WhatsApp Business API oficial, quando
    # existir, é só mudar o que esta função retorna.
    return WhatsAppClickToChatCheckout()
