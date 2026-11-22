"""LLM-as-judge: usa a MESMA porta `revold_ai_assistant.ports.LLMProvider` que
o assistente usa para responder — reaproveita o mecanismo de troca de
provedor por configuração (`LLM_PROVIDER`) em vez de inventar um cliente de
avaliação à parte. Só produz uma nota que significa alguma coisa quando o
provider configurado é um modelo de verdade (Azure OpenAI); com o provider
`dev` ou o `FakeLLMProvider` de teste, a resposta não é um JSON de nota de
verdade — por isso `test_llm_judge.py` só roda com `LLM_PROVIDER=azure-openai`
configurado (ver `real_llm_provider_configured()`), pulando (skip) sozinho
caso contrário, mesma convenção dos testes de integração contra Azure SQL
real."""
from __future__ import annotations

import json
import os
import re

from revold_ai_assistant.adapters.llm.factory import LLMSettings
from revold_ai_assistant.domain import ChatMessage, Role
from revold_ai_assistant.ports import LLMProvider

_JUDGE_SYSTEM_PROMPT = """Você é um avaliador de qualidade de atendimento ao \
cliente de uma loja de roupas. Vai receber a pergunta de um cliente, a \
resposta que a assistente virtual da loja deu, e um critério específico \
para este caso. Avalie de 0 (péssimo) a 10 (ótimo) cada um destes quatro \
critérios e responda SOMENTE com um objeto JSON, sem nenhum texto antes ou \
depois, no formato exato:

{"relevancia": <0-10>, "gramatica": <0-10>, "tom": <0-10>, "resolucao": <0-10>}

- relevancia: a resposta tem a ver com o que foi perguntado?
- gramatica: o português está correto?
- tom: profissional, simpático, sem deboche?
- resolucao: atende ao critério específico do caso (abaixo)?"""

_SCORE_KEYS = ("relevancia", "gramatica", "tom", "resolucao")


def real_llm_provider_configured() -> bool:
    """True só quando LLM_PROVIDER=azure-openai — o único caso em que o
    LLMProvider configurado é um modelo de verdade capaz de julgar outra
    resposta de forma que signifique alguma coisa."""
    return os.environ.get("LLM_PROVIDER") == "azure-openai"


def llm_settings_from_environment() -> LLMSettings:
    """A configuracao do LLM a partir do ambiente de quem roda o eval.

    Codigo de teste pode ler o ambiente; o `src/` do dominio nao pode. Por isso a
    leitura fica aqui, e a factory do dominio recebe a configuracao pronta.
    """
    return LLMSettings.from_mapping({k: v for k, v in os.environ.items() if v.strip()})


class JudgeResponseInvalido(Exception):
    """O juiz não devolveu o JSON esperado — não é o mesmo que uma nota
    baixa, é a infraestrutura de avaliação falhando, e o teste que chamou
    isto deveria falhar de forma clara em vez de silenciosamente tratar
    como nota zero."""


def _parse_scores(raw: str) -> dict[str, float]:
    # Modelos às vezes envolvem o JSON em ```json ... ``` mesmo quando
    # instruídos a não fazer isso — tolera isso sem tolerar lixo de verdade.
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match is None:
        raise JudgeResponseInvalido(f"Juiz não devolveu JSON reconhecível: {raw!r}")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise JudgeResponseInvalido(f"JSON do juiz é inválido: {raw!r}") from exc

    scores: dict[str, float] = {}
    for key in _SCORE_KEYS:
        if key not in data:
            raise JudgeResponseInvalido(f"Juiz não avaliou o critério '{key}': {data!r}")
        try:
            scores[key] = float(data[key])
        except (TypeError, ValueError) as exc:
            raise JudgeResponseInvalido(f"Nota de '{key}' não é numérica: {data[key]!r}") from exc
    return scores


async def judge_reply(
    llm: LLMProvider, *, question: str, reply: str, criterio: str
) -> dict[str, float]:
    """Pede pro `llm` avaliar `reply` dado `question` e o `criterio`
    específico do caso. Devolve {"relevancia": X, "gramatica": X, "tom": X,
    "resolucao": X}, cada X de 0.0 a 10.0. Levanta JudgeResponseInvalido se
    a resposta não puder ser interpretada como o JSON esperado."""
    user_message = (
        f"Pergunta do cliente: {question or '(pergunta vazia)'}\n"
        f"Resposta da assistente: {reply}\n"
        f"Critério específico deste caso: {criterio}"
    )
    raw = await llm.complete(
        system_prompt=_JUDGE_SYSTEM_PROMPT,
        messages=[ChatMessage(role=Role.USER, content=user_message)],
    )
    return _parse_scores(raw)
