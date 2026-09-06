"""Testa só o parsing de `core_ai_assistant_evals.judge` — não precisa de
LLM real nem do marker `eval` (é lógica pura), então roda sempre, inclusive
sem nenhum provider configurado."""
from __future__ import annotations

from collections.abc import Sequence

import pytest

from core_ai_assistant.domain import ChatMessage
from core_ai_assistant_evals.judge import JudgeResponseInvalido, judge_reply


class _StubLLM:
    provider_name = "stub"

    def __init__(self, response: str) -> None:
        self._response = response

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    async def complete(self, *, system_prompt: str, messages: Sequence[ChatMessage]) -> str:
        return self._response


async def test_parseia_json_limpo() -> None:
    llm = _StubLLM('{"relevancia": 9, "gramatica": 10, "tom": 8, "resolucao": 7}')
    scores = await judge_reply(llm, question="q", reply="r", criterio="c")
    assert scores == {"relevancia": 9.0, "gramatica": 10.0, "tom": 8.0, "resolucao": 7.0}


async def test_tolera_json_envolvido_em_markdown() -> None:
    llm = _StubLLM(
        '```json\n{"relevancia": 6, "gramatica": 6, "tom": 6, "resolucao": 6}\n```'
    )
    scores = await judge_reply(llm, question="q", reply="r", criterio="c")
    assert scores["relevancia"] == 6.0


async def test_texto_sem_json_levanta_erro_explicito() -> None:
    llm = _StubLLM("Desculpe, não consigo avaliar isso.")
    with pytest.raises(JudgeResponseInvalido):
        await judge_reply(llm, question="q", reply="r", criterio="c")


async def test_json_faltando_criterio_levanta_erro_explicito() -> None:
    llm = _StubLLM('{"relevancia": 9, "gramatica": 10, "tom": 8}')
    with pytest.raises(JudgeResponseInvalido, match="resolucao"):
        await judge_reply(llm, question="q", reply="r", criterio="c")


async def test_nota_nao_numerica_levanta_erro_explicito() -> None:
    llm = _StubLLM('{"relevancia": "alta", "gramatica": 10, "tom": 8, "resolucao": 7}')
    with pytest.raises(JudgeResponseInvalido):
        await judge_reply(llm, question="q", reply="r", criterio="c")
