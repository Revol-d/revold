from __future__ import annotations

from collections.abc import Sequence

import pytest

from revold_ai_assistant.domain import ChatMessage, RetrievedProduct


class FakeLLMProvider:
    """Mesmo fake usado em libs/domains/ai-assistant/tests/conftest.py,
    duplicado aqui de propósito — cada suíte de teste deste monorepo mantém
    seus próprios fakes, sem importar fixtures de outro pacote (mesmo
    padrão usado em apps/ecommerce/api-gateway/tests)."""

    provider_name = "fake"

    async def embed(self, text: str) -> list[float]:
        return [float(len(text)), float(text.count("a"))]

    async def complete(self, *, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        return "[fake] resposta"


class FakeProductIndex:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[str, str, list[float]]] = {}

    async def upsert(
        self, *, sku: str, name: str, description: str, embedding: list[float]
    ) -> None:
        self._entries[sku] = (name, description, embedding)

    async def search(self, *, embedding: list[float], limit: int) -> list[RetrievedProduct]:
        def _distance(entry_embedding: list[float]) -> float:
            return sum((a - b) ** 2 for a, b in zip(embedding, entry_embedding, strict=True))

        ranked = sorted(
            (
                RetrievedProduct(sku=sku, name=name, distance=_distance(vec))
                for sku, (name, _description, vec) in self._entries.items()
            ),
            key=lambda p: p.distance,
        )
        return ranked[:limit]


@pytest.fixture
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def fake_index() -> FakeProductIndex:
    return FakeProductIndex()
