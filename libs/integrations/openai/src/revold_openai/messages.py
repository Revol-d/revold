"""Uma fala de conversa no formato que os clientes de chat entendem. Sem I/O."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ChatTurnRole = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class ChatTurn:
    """Quem falou e o que falou. A instrução de sistema vai separada, na chamada."""

    role: ChatTurnRole
    content: str
