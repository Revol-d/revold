"""Casos de uso do core-ai-assistant.

AskAssistant orquestra o fluxo do agente com LangGraph (ver ADR-0011):
retrieve (busca produtos relevantes via RAG) -> generate (chama o LLM com
esse contexto) -> decide_escalation (heurística provisória de intenção de
compra). LangGraph aqui é biblioteca de domínio do core, não infraestrutura
web — não fere a regra de core não depender de FastAPI (ADR-0002).
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from langgraph.graph import END, StateGraph

from core_ai_assistant.domain import AssistantReply, ChatMessage, RetrievedProduct, Role
from core_ai_assistant.ports import LLMProvider, ProductIndex

_RETRIEVAL_LIMIT = 3

# Heurística provisória de intenção de compra (ver ADR-0011: um classificador
# de intenção via LLM é o passo natural assim que houver provedor real em
# produção — não faz sentido pedir isso de um provider dev sem modelo).
_PURCHASE_INTENT_KEYWORDS = (
    "quero comprar",
    "quero levar",
    "fechar pedido",
    "fechar compra",
    "finalizar compra",
    "como pago",
    "como faço para comprar",
    "quero fazer o pedido",
)


class IndexProduct:
    """Embeda e indexa um produto do catálogo (upsert)."""

    def __init__(self, llm: LLMProvider, index: ProductIndex) -> None:
        self._llm = llm
        self._index = index

    async def execute(self, *, sku: str, name: str, description: str) -> None:
        embedding = await self._llm.embed(f"{name}\n{description}".strip())
        await self._index.upsert(sku=sku, name=name, description=description, embedding=embedding)


def _build_system_prompt(retrieved: Sequence[RetrievedProduct]) -> str:
    base = (
        "Você é a assistente virtual da loja da Nick. Responda de forma breve, "
        "simpática e honesta — nunca invente produto que não esteja listado. "
        "Você não fecha pedido sozinha: se o cliente quiser comprar, "
        "direcione para falar com a Nick pelo WhatsApp."
    )
    if not retrieved:
        return base
    produtos = "\n".join(f"- {p.name} (SKU {p.sku})" for p in retrieved)
    return f"{base}\n\nProdutos do catálogo relevantes para a pergunta:\n{produtos}"


def _has_purchase_intent(question: str) -> bool:
    lowered = question.lower()
    return any(keyword in lowered for keyword in _PURCHASE_INTENT_KEYWORDS)


class _AssistantState(TypedDict):
    history: list[ChatMessage]
    question: str
    retrieved: list[RetrievedProduct]
    reply: str
    escalate: bool


def _build_graph(llm: LLMProvider, index: ProductIndex):
    async def retrieve(state: _AssistantState) -> dict:
        embedding = await llm.embed(state["question"])
        retrieved = await index.search(embedding=embedding, limit=_RETRIEVAL_LIMIT)
        return {"retrieved": retrieved}

    async def generate(state: _AssistantState) -> dict:
        system_prompt = _build_system_prompt(state["retrieved"])
        messages = [*state["history"], ChatMessage(role=Role.USER, content=state["question"])]
        reply = await llm.complete(system_prompt=system_prompt, messages=messages)
        return {"reply": reply}

    async def decide_escalation(state: _AssistantState) -> dict:
        return {"escalate": _has_purchase_intent(state["question"])}

    graph = StateGraph(_AssistantState)
    graph.add_node("retrieve", retrieve)
    graph.add_node("generate", generate)
    graph.add_node("decide_escalation", decide_escalation)
    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", "decide_escalation")
    graph.add_edge("decide_escalation", END)
    return graph.compile()


class AskAssistant:
    def __init__(self, llm: LLMProvider, index: ProductIndex) -> None:
        self._graph = _build_graph(llm, index)

    async def execute(self, *, history: Sequence[ChatMessage], question: str) -> AssistantReply:
        result = await self._graph.ainvoke(
            {
                "history": list(history),
                "question": question,
                "retrieved": [],
                "reply": "",
                "escalate": False,
            }
        )
        return AssistantReply(
            message=result["reply"],
            escalate_to_whatsapp=result["escalate"],
            retrieved_products=tuple(result["retrieved"]),
        )
