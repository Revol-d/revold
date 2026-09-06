"""Testes de core_events.domain.DomainEvent."""
from __future__ import annotations

import pytest

from core_events.domain import DomainEvent


def test_cria_evento_valido() -> None:
    event = DomainEvent(name="product.updated", payload={"sku": "CAM-001"})
    assert event.name == "product.updated"
    assert event.payload == {"sku": "CAM-001"}


def test_payload_e_opcional() -> None:
    event = DomainEvent(name="catalog.reindex_requested")
    assert event.payload == {}


def test_name_vazio_levanta_erro() -> None:
    with pytest.raises(ValueError, match="não pode ser vazio"):
        DomainEvent(name="")


def test_name_sem_ponto_levanta_erro() -> None:
    """Força a convenção <contexto>.<acontecimento> — evita nomes soltos tipo
    "updated" que não dizem de onde vieram, e ajuda quem for adicionar um
    handler novo a achar rápido o publisher correspondente."""
    with pytest.raises(ValueError, match="contexto"):
        DomainEvent(name="updated")


def test_eventos_sao_imutaveis() -> None:
    event = DomainEvent(name="stock.low", payload={"sku": "A"})
    with pytest.raises(AttributeError):
        event.name = "outro"  # type: ignore[misc]
