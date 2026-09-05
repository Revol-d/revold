"""Teste de contrato do router de ai-assistant: sobe o app FastAPI de
verdade, com LLMProvider, ProductIndex e ProductRepository trocados por
fakes em memória."""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from api_gateway.dependencies import (
    get_llm_provider,
    get_product_index,
    get_product_repository,
)
from api_gateway.main import app
from api_gateway.security import get_current_user
from core_ai_assistant.domain import ChatMessage, RetrievedProduct, Role
from core_catalog.domain import Category, Money, Product, ProductVariant
from core_identity.domain import AuthenticatedUser
from core_identity.domain import Role as UserRole


class _FakeLLMProvider:
    provider_name = "fake"

    async def embed(self, text: str) -> list[float]:
        return [float(len(text)), float(text.count("a"))]

    async def complete(self, *, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        last_user = next(
            (m.content for m in reversed(messages) if m.role == Role.USER), ""
        )
        if "Produtos do catálogo" in system_prompt:
            return f"[fake] encontrei produtos para: {last_user}"
        return f"[fake] sem produtos para: {last_user}"


class _FakeProductIndex:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[str, str, list[float]]] = {}

    async def upsert(
        self, *, sku: str, name: str, description: str, embedding: list[float]
    ) -> None:
        self._entries[sku] = (name, description, embedding)

    async def search(self, *, embedding: list[float], limit: int) -> list[RetrievedProduct]:
        def _distance(vec: list[float]) -> float:
            return sum((a - b) ** 2 for a, b in zip(embedding, vec, strict=True))

        ranked = sorted(
            (
                RetrievedProduct(sku=sku, name=name, distance=_distance(vec))
                for sku, (name, _description, vec) in self._entries.items()
            ),
            key=lambda p: p.distance,
        )
        return ranked[:limit]


class _FakeProductRepository:
    def __init__(self, products: list[Product]) -> None:
        self._products = products

    async def list_categories(self):
        return []

    async def list_products(self, *, category_slug, page, page_size):
        start = (page - 1) * page_size
        end = start + page_size
        return self._products[start:end], len(self._products)

    async def get_product(self, sku):
        return next((p for p in self._products if p.sku == sku), None)


def _make_product(sku: str) -> Product:
    return Product(
        sku=sku,
        name=f"Produto {sku}",
        category=Category(slug="vestidos", name="Vestidos"),
        price=Money(amount=Decimal("99.90")),
        variants=[ProductVariant(sku=f"{sku}-M", size="M", color="Azul", in_stock=True)],
        description=f"Descrição do produto {sku}",
    )


_STAFF_USER = AuthenticatedUser(
    external_id="staff-1", provider="dev", email="staff@example.com", name="Staff",
    roles=(UserRole.STAFF,),
)
_CUSTOMER_USER = AuthenticatedUser(
    external_id="cust-1", provider="dev", email="cliente@example.com", name="Cliente",
    roles=(UserRole.CUSTOMER,),
)


@pytest.fixture
def fake_index() -> _FakeProductIndex:
    return _FakeProductIndex()


@pytest.fixture(autouse=True)
def override_dependencies(fake_index: _FakeProductIndex):
    app.dependency_overrides[get_llm_provider] = lambda: _FakeLLMProvider()
    app.dependency_overrides[get_product_index] = lambda: fake_index
    app.dependency_overrides[get_product_repository] = lambda: _FakeProductRepository(
        [_make_product("A")]
    )
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_ask_sem_produtos_indexados(client: AsyncClient) -> None:
    response = await client.post("/api/assistant/ask", json={"question": "Vocês têm bolsas?"})
    assert response.status_code == 200
    body = response.json()
    assert body["retrieved_products"] == []
    assert body["escalate_to_whatsapp"] is False


async def test_ask_com_intencao_de_compra_escala(client: AsyncClient) -> None:
    response = await client.post(
        "/api/assistant/ask", json={"question": "Quero comprar, como faço?"}
    )
    assert response.status_code == 200
    assert response.json()["escalate_to_whatsapp"] is True


async def test_reindex_sem_autenticacao_retorna_401(client: AsyncClient) -> None:
    response = await client.post("/api/assistant/reindex")
    assert response.status_code == 401


async def test_reindex_com_papel_customer_retorna_403(client: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = lambda: _CUSTOMER_USER
    response = await client.post("/api/assistant/reindex")
    assert response.status_code == 403


async def test_reindex_com_papel_staff_indexa_catalogo(
    client: AsyncClient, fake_index: _FakeProductIndex
) -> None:
    app.dependency_overrides[get_current_user] = lambda: _STAFF_USER
    response = await client.post("/api/assistant/reindex")
    assert response.status_code == 200
    assert response.json()["products_indexed"] == 1

    ask_response = await client.post("/api/assistant/ask", json={"question": "Produto A"})
    assert ask_response.json()["retrieved_products"][0]["sku"] == "A"
