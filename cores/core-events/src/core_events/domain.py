"""Entidade central de evento de domínio."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Um evento de domínio publicado por algum core, consumido de forma
    assíncrona por um worker (ver workers/event-worker).

    `name` segue a convenção `<contexto>.<acontecimento>` (ex.:
    "product.updated", "checkout.created", "stock.low") — é a chave que o
    consumidor usa para rotear pro handler certo (ver
    workers/event-worker/src/event_worker/handlers.py). `payload` carrega só
    primitivos serializáveis (str/int/float/bool/None e dict/list disso),
    nunca uma entidade de outro core — quem publica já traduziu para
    primitivos antes de chamar `EventPublisher.publish`, do mesmo jeito que
    core_notification.use_cases já faz para Notification.
    """

    name: str
    payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name não pode ser vazio")
        if "." not in self.name:
            raise ValueError(
                f"name deve seguir a convenção '<contexto>.<acontecimento>' (recebido: {self.name!r})"
            )
