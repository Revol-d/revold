"""Entidades do domínio de notificação."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Notification:
    """Uma notificação a ser enviada para a Nick por algum canal.

    event_type identifica a origem/categoria do evento (ex.: "new_checkout",
    "low_stock") — útil para log e, futuramente, para permitir que a Nick
    silencie categorias específicas sem mudar código.
    """

    event_type: str
    message: str

    def __post_init__(self) -> None:
        if not self.event_type:
            raise ValueError("event_type não pode ser vazio")
        if not self.message:
            raise ValueError("message não pode ser vazio")
