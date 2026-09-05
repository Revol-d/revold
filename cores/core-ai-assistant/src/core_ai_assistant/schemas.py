"""Schemas Pydantic que espelham contracts/api/ai-assistant.yaml."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessageSchema(BaseModel):
    role: str
    content: str


class AskAssistantRequestSchema(BaseModel):
    question: str
    history: list[ChatMessageSchema] = Field(default_factory=list)


class RetrievedProductSchema(BaseModel):
    sku: str
    name: str


class AssistantReplySchema(BaseModel):
    message: str
    escalate_to_whatsapp: bool
    retrieved_products: list[RetrievedProductSchema] = Field(default_factory=list)


class ReindexResultSchema(BaseModel):
    products_indexed: int
