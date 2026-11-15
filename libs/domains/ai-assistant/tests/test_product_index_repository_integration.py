"""Testes de integração do PostgresProductIndexRepository (RAG, ADR-0011)
contra um Postgres real com pgvector — igual espírito de
test_catalog_repository_integration.py, mas para o índice vetorial. Nunca
tinha nenhum teste, nem contra fake: a busca por similaridade usa
`cosine_distance` do operador pgvector, que só existe rodando contra SQL de
verdade — não dá pra simular em memória com confiança de que o operador da
extensão está sendo usado corretamente (nome do método, direção da
distância, ORDER BY certo).

Pula (skip) automaticamente se TEST_DATABASE_URL/DATABASE_URL não apontar
pra um Postgres alcançável — mesma convenção do arquivo de catálogo."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from revold_ai_assistant.adapters.postgres.models import EMBEDDING_DIMENSIONS
from revold_ai_assistant.adapters.postgres.repository import PostgresProductIndexRepository

pytestmark = pytest.mark.integration

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL", "postgresql+asyncpg://revold:revold_dev_only@localhost:5432/revold"
    ),
)


def _basis_vector(dimension_with_one: int) -> list[float]:
    """Vetor com 1.0 numa posição e 0.0 no resto — dá pra prever a distância
    de cosseno exata entre dois destes (0.0 se mesma posição, 1.0 se
    diferente), sem depender de embedding real."""
    vector = [0.0] * EMBEDDING_DIMENSIONS
    vector[dimension_with_one] = 1.0
    return vector


@pytest.fixture
async def repository():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — qualquer falha de conexão vira skip
        await engine.dispose()
        pytest.skip(f"Postgres de teste não disponível em {TEST_DATABASE_URL}: {exc}")

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(text("TRUNCATE ai_assistant_product_index RESTART IDENTITY CASCADE"))
        await session.commit()
        yield PostgresProductIndexRepository(session)
    await engine.dispose()


class TestUpsertEBusca:
    async def test_upsert_de_sku_existente_atualiza_em_vez_de_duplicar(
        self, repository: PostgresProductIndexRepository
    ) -> None:
        await repository.upsert(
            sku="CAM-001", name="Camiseta v1", description="descrição antiga", embedding=_basis_vector(0)
        )
        await repository.upsert(
            sku="CAM-001", name="Camiseta v2", description="descrição nova", embedding=_basis_vector(1)
        )

        resultados = await repository.search(embedding=_basis_vector(1), limit=10)
        assert len(resultados) == 1
        assert resultados[0].name == "Camiseta v2"

    async def test_busca_ordena_por_distancia_de_cosseno_real(
        self, repository: PostgresProductIndexRepository
    ) -> None:
        await repository.upsert(
            sku="A", name="Produto A", description="", embedding=_basis_vector(0)
        )
        await repository.upsert(
            sku="B", name="Produto B", description="", embedding=_basis_vector(1)
        )
        await repository.upsert(
            sku="C", name="Produto C", description="", embedding=_basis_vector(2)
        )

        # Consulta exatamente igual ao vetor de B -> B tem que vir primeiro
        # (distância 0), A e C empatados depois (ortogonais, distância 1).
        resultados = await repository.search(embedding=_basis_vector(1), limit=3)

        assert [r.sku for r in resultados] == ["B", "A", "C"] or [r.sku for r in resultados] == [
            "B",
            "C",
            "A",
        ]
        assert resultados[0].sku == "B"
        assert resultados[0].distance == pytest.approx(0.0, abs=1e-6)
        assert resultados[1].distance == pytest.approx(1.0, abs=1e-6)

    async def test_limit_restringe_quantidade_de_resultados(
        self, repository: PostgresProductIndexRepository
    ) -> None:
        for i in range(5):
            await repository.upsert(
                sku=f"SKU-{i}", name=f"Produto {i}", description="", embedding=_basis_vector(i)
            )

        resultados = await repository.search(embedding=_basis_vector(0), limit=2)
        assert len(resultados) == 2

    async def test_busca_sem_nada_indexado_retorna_vazio(
        self, repository: PostgresProductIndexRepository
    ) -> None:
        resultados = await repository.search(embedding=_basis_vector(0), limit=5)
        assert resultados == []
