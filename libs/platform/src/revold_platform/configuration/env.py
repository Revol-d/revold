"""Um parser de ambiente só.

As regras: texto vazio ou só com espaço conta como ausente, `bool` aceita `1/true/yes/on` (sem
diferenciar maiúscula) e inteiro inválido volta ao padrão com aviso, nunca com exceção. Config
errada não derruba a partida.

Lê na CHAMADA, nunca no import: valor lido no import fica congelado, e teste que muda o ambiente
passa a ver o valor velho.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_TRUE = frozenset({"1", "true", "yes", "on"})


def env_str(name: str, default: str | None = None) -> str | None:
    """Texto do ambiente, sem espaços nas pontas. Vazio conta como ausente."""
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else default


def env_bool(name: str, default: bool = False) -> bool:
    """`1`, `true`, `yes` ou `on` (qualquer caixa) é verdadeiro; o resto, falso. Ausente: o padrão."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in _TRUE


def env_int(name: str, default: int) -> int:
    """Inteiro do ambiente. Valor inválido vira o padrão, com aviso, nunca exceção."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    try:
        return int(value.strip())
    except ValueError:
        logger.warning("%s=%r nao e inteiro; usando %d.", name, value, default)
        return default


def env_list(name: str, *, separator: str = ",") -> list[str]:
    """Lista separada por vírgula, sem itens vazios nem espaços nas pontas. Ausente: lista vazia."""
    raw = os.environ.get(name, "")
    return [item.strip() for item in raw.split(separator) if item.strip()]


def env_required(name: str, *, purpose: str) -> str:
    """Valor obrigatório. Ausente levanta com uma mensagem que diz **para que** serve.

    Use quando a falta impede a operação: o erro aparece na montagem, com o nome da variável e
    o motivo, em vez de virar um `None` que estoura três camadas adiante.
    """
    value = env_str(name)
    if not value:
        raise ValueError(
            f"Variavel de ambiente {name} ausente ou vazia. Necessaria para: {purpose}."
        )
    return value


def env_snapshot() -> dict[str, str]:
    """Cópia do ambiente, só com as variáveis que têm valor (vazio conta como ausente).

    É o que o `settings.py` de um app entrega ao `from_mapping` de um grupo de configuração de
    uma lib (o provedor de LLM, o canal de notificação). A lib sabe o nome das chaves do grupo
    dela; quem toca `os.environ` é só este módulo.
    """
    return {name: value.strip() for name, value in os.environ.items() if value and value.strip()}
