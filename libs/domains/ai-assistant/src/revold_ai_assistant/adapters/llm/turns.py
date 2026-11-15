"""Traduz a conversa do domínio (`ChatMessage`) para as falas que os clientes de chat entendem."""

from __future__ import annotations

from collections.abc import Sequence

from revold_ai_assistant.domain import ChatMessage, Role
from revold_openai.messages import ChatTurn


def to_chat_turns(messages: Sequence[ChatMessage]) -> list[ChatTurn]:
    """Quem não é o usuário é o assistente: o domínio só tem esses dois papéis na conversa."""
    return [
        ChatTurn(role="user" if message.role == Role.USER else "assistant", content=message.content)
        for message in messages
    ]
