"""Roda o dataset comportamental inteiro (`core_ai_assistant_evals.dataset`)
contra o `FakeLLMProvider`/`FakeProductIndex` — determinístico, sem
credencial, roda sempre (inclusive no CI). Testa a ORQUESTRAÇÃO (a
heurística de escalar pro WhatsApp, se a busca no índice aconteceu), não a
qualidade do texto gerado — isso é `test_llm_judge.py`, que só roda de
verdade com um LLM real configurado.

Amplia a cobertura de `cores/core-ai-assistant/tests/test_use_cases.py`
(6 casos escolhidos a dedo) para as 14 perguntas do dataset, incluindo
gírias/emoji, pergunta vazia, texto longo, e cada frase-gatilho de intenção
de compra separadamente — regressão bem mais ampla pro fluxo do LangGraph
sem precisar de nenhuma credencial."""
from __future__ import annotations

import pytest

from core_ai_assistant.use_cases import AskAssistant, IndexProduct
from core_ai_assistant_evals.dataset import DATASET
from core_ai_assistant_evals.fakes import FakeLLMProvider, FakeProductIndex

pytestmark = pytest.mark.eval


@pytest.mark.parametrize("case", DATASET, ids=[c.id for c in DATASET])
async def test_comportamento_do_caso(case) -> None:  # noqa: ANN001 — EvalCase não é público fora do dataset
    llm = FakeLLMProvider()
    index = FakeProductIndex()
    for product in case.catalog:
        await IndexProduct(llm, index).execute(
            sku=product.sku, name=product.name, description=product.description
        )

    reply = await AskAssistant(llm, index).execute(history=case.history, question=case.question)

    assert reply.escalate_to_whatsapp is case.expect_escalation, (
        f"esperava escalate_to_whatsapp={case.expect_escalation} para {case.id!r}"
    )
    tem_produto_recuperado = len(reply.retrieved_products) > 0
    assert tem_produto_recuperado is case.expect_retrieval, (
        f"esperava retrieval={case.expect_retrieval} para {case.id!r}, "
        f"veio {len(reply.retrieved_products)} produto(s)"
    )
    # Robustez mínima: nenhum caso (nem pergunta vazia, nem texto longo)
    # deveria fazer o assistente devolver uma resposta vazia.
    assert reply.message.strip() != ""


async def test_limite_de_recuperacao_nunca_passa_de_tres() -> None:
    caso = next(c for c in DATASET if c.id == "multiplos_produtos_respeita_limite_de_recuperacao")
    assert len(caso.catalog) > 3  # confere a premissa do teste: mais produtos que o limite

    llm = FakeLLMProvider()
    index = FakeProductIndex()
    for product in caso.catalog:
        await IndexProduct(llm, index).execute(
            sku=product.sku, name=product.name, description=product.description
        )

    reply = await AskAssistant(llm, index).execute(history=(), question=caso.question)
    assert len(reply.retrieved_products) <= 3
