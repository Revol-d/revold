"""Testes de revold_platform.events.domain.DomainEvent."""
from __future__ import annotations

import pytest
from revold_testing.events_factories import DomainEventFactory

from revold_platform.events.domain import DomainEvent


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


class TestFabricaDeDados:
    def test_fabrica_gera_apenas_nomes_do_conjunto_conhecido_pelo_worker(self) -> None:
        # A plataforma nunca importa um app (regra de dependência, ADR-0027:
        # a seta só desce) — por isso a lista abaixo é um literal, mantido em
        # sincronia à mão com o if/elif de
        # `apps/ecommerce/event-worker/src/event_worker/celery_app.py::_dispatch`.
        # O que essa fábrica evita é o risco oposto: gerar
        # "<palavra>.<palavra>" aleatório que passa na validação de
        # domínio mas não corresponde a nenhum evento real do sistema.
        nomes_conhecidos = {
            "product.updated",
            "checkout.created",
            "stock.low",
            "catalog.reindex_requested",
        }
        for _ in range(10):
            event = DomainEventFactory()
            assert "." in event.name
            assert isinstance(event.payload, dict)
            assert event.name in nomes_conhecidos
