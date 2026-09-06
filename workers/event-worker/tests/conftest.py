from __future__ import annotations

from collections.abc import Sequence

import pytest

from core_ai_assistant.domain import ChatMessage, RetrievedProduct


class FakeLLMProvider:
    """Mesmo fake usado nas outras suítes deste monorepo, duplicado de
    propósito (cada pacote mantém seus próprios fakes — ver
    workers/catalog-indexer/tests/conftest.py)."""

    provider_name = "fake"

    async def embed(self, text: str) -> list[float]:
        return [float(len(text)), float(text.count("a"))]

    async def complete(self, *, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        return "[fake] resposta"


class FakeProductIndex:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[str, str, list[float]]] = {}

    async def upsert(self, *, sku: str, name: str, description: str, embedding: list[float]) -> None:
        self._entries[sku] = (name, description, embedding)

    async def search(self, *, embedding: list[float], limit: int) -> list[RetrievedProduct]:
        return [
            RetrievedProduct(sku=sku, name=name, distance=0.0)
            for sku, (name, _desc, _vec) in list(self._entries.items())[:limit]
        ]


@pytest.fixture
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def fake_index() -> FakeProductIndex:
    return FakeProductIndex()
