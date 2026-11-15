"""Avaliação de QUALIDADE de resposta (LLM-as-judge) — ao contrário de
`test_behavior.py`, só faz sentido rodar com um LLM de verdade dos dois
lados (gerando a resposta E julgando): com `LLM_PROVIDER=dev`, a resposta é
sempre o mesmo texto de regra fixa, então "avaliar a qualidade" dela não
mediria nada real. Por isso pula (skip) inteiro sem `LLM_PROVIDER=azure-openai`
e a credencial de verdade configurada — mesma convenção dos testes de
integração contra Postgres real (skip gracioso, nunca falha o CI por falta
de credencial).

Rodar de verdade (com as credenciais reais no ambiente/.env, ver ADR-0011):
    LLM_PROVIDER=azure-openai uv run pytest -m eval -v
"""
from __future__ import annotations

import pytest

from revold_ai_assistant.adapters.llm.factory import build_llm_provider
from revold_ai_assistant.application.use_cases import AskAssistant, IndexProduct
from revold_ai_assistant_evals.dataset import DATASET
from revold_ai_assistant_evals.fakes import FakeProductIndex
from revold_ai_assistant_evals.judge import (
    judge_reply,
    llm_settings_from_environment,
    real_llm_provider_configured,
)

pytestmark = [
    pytest.mark.eval,
    pytest.mark.skipif(
        not real_llm_provider_configured(),
        reason=(
            "Avaliação de qualidade via LLM-as-judge exige LLM_PROVIDER=azure-openai com "
            "credencial real — ver .env.example e ADR-0011. Sem isso o teste não mede nada "
            "de verdade (LLM_PROVIDER=dev sempre devolve o mesmo texto fixo)."
        ),
    ),
]

# Nota mínima aceitável por critério (0-10) — limiar deliberadamente
# permissivo (nota de aprovação, não de excelência): o objetivo deste teste
# é pegar regressão óbvia de qualidade (resposta grosseira, errada,
# desconexa), não substituir revisão humana.
_NOTA_MINIMA = 5.0


@pytest.mark.parametrize("case", DATASET, ids=[c.id for c in DATASET])
async def test_qualidade_da_resposta_via_llm_de_verdade(case) -> None:  # noqa: ANN001
    llm = build_llm_provider(llm_settings_from_environment())
    index = FakeProductIndex()
    for product in case.catalog:
        await IndexProduct(llm, index).execute(
            sku=product.sku, name=product.name, description=product.description
        )

    reply = await AskAssistant(llm, index).execute(history=case.history, question=case.question)

    scores = await judge_reply(
        llm, question=case.question, reply=reply.message, criterio=case.criterio_qualidade
    )

    abaixo_do_minimo = {k: v for k, v in scores.items() if v < _NOTA_MINIMA}
    assert not abaixo_do_minimo, (
        f"caso {case.id!r} ficou abaixo da nota mínima em {abaixo_do_minimo} "
        f"(resposta avaliada: {reply.message!r})"
    )
