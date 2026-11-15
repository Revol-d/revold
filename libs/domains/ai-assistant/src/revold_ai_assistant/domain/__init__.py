"""Entidades e value objects do assistente de IA (ADR-0011)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class RetrievedProduct:
    """Um produto do catálogo encontrado pela busca por similaridade (RAG).

    `distance` é a distância (não similaridade) do embedding da pergunta ao
    embedding do produto — quanto menor, mais relevante.
    """

    sku: str
    name: str
    distance: float


@dataclass(frozen=True, slots=True)
class AssistantReply:
    message: str
    escalate_to_whatsapp: bool
    retrieved_products: tuple[RetrievedProduct, ...] = ()
