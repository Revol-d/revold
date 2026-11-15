"""`LLMProvider`/`ProductIndex` fakes em memória — movidos de
`libs/domains/ai-assistant/tests/conftest.py` (que continua expondo as
mesmas classes como fixtures `fake_llm`/`fake_index`, sem mudança de
comportamento) para cá, um módulo importável de verdade, porque o dataset
de evals (`evals/test_behavior.py`) também precisa deles e fica fora da
árvore de `tests/` (fixtures de `conftest.py` só valem para o próprio
diretório e subdiretórios, não para um diretório irmão)."""
from __future__ import annotations

from collections.abc import Sequence

from revold_ai_assistant.domain import ChatMessage, RetrievedProduct, Role


class FakeLLMProvider:
    """Adapter fake em memória, mesma forma da porta LLMProvider, só para teste.

    embed() é determinístico (mesmo texto -> mesmo vetor curto, baseado no
    tamanho do texto) e complete() é uma regra simples e previsível — nada
    de modelo de verdade, só o suficiente para exercitar o fluxo.
    """

    provider_name = "fake"

    def __init__(self) -> None:
        self.embed_calls: list[str] = []
        self.complete_calls: list[tuple[str, tuple[ChatMessage, ...]]] = []

    async def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return [float(len(text)), float(text.count("a"))]

    async def complete(self, *, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        self.complete_calls.append((system_prompt, tuple(messages)))
        last_user = next(
            (m.content for m in reversed(messages) if m.role == Role.USER), ""
        )
        if "Produtos do catálogo" in system_prompt:
            return f"[fake] encontrei produtos para: {last_user}"
        return f"[fake] sem produtos para: {last_user}"


class FakeProductIndex:
    """Adapter fake em memória, mesma forma da porta ProductIndex, só para teste."""

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
