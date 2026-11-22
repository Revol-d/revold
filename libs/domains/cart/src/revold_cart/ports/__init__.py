"""Porta de persistência do carrinho.

A primeira implementação (revold_cart.adapters.redis.repository) usa
Redis com TTL — o carrinho é efêmero por natureza (ver ADR de stack: Redis
já fazia parte da arquitetura para cache/sessão). Nada aqui depende de Redis
especificamente; um adapter de outro provedor seria só uma segunda implementação
desta porta, se um dia fizer sentido (ex.: carrinho "salvo" por muito tempo
para usuário logado).
"""
from __future__ import annotations

from typing import Protocol

from revold_cart.domain import Cart


class CartRepository(Protocol):
    async def get(self, cart_id: str) -> Cart | None: ...

    async def save(self, cart: Cart) -> None: ...

    async def delete(self, cart_id: str) -> None: ...
