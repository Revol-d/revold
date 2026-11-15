"""Entidades do domínio de configuração da loja (ADR-0019)."""
from __future__ import annotations

import re
from dataclasses import dataclass

_CNPJ_DIGITS = re.compile(r"\D")


def _only_digits(value: str) -> str:
    return _CNPJ_DIGITS.sub("", value)


@dataclass(frozen=True, slots=True)
class StoreSettings:
    """Configuração administrativa da loja — um único registro (não há
    múltiplas lojas hoje, ver ADR-0019), editável pela Nick no
    admin-dashboard.

    `cnpj` aceita tanto o formato mascarado (`00.000.000/0000-00`) quanto
    só os dígitos — só os dígitos são validados/comparados, a máscara é
    responsabilidade do frontend. Todo campo textual pode ficar vazio
    (loja recém-criada, ainda sem os dados preenchidos) exceto `cnpj`
    e `contact_email` quando informados — se informados, precisam ter
    forma válida; string vazia é o único jeito de representar "ainda não
    preenchido".
    """

    cnpj: str
    store_name: str
    contact_email: str
    contact_phone: str
    store_address: str
    low_stock_threshold: int

    def __post_init__(self) -> None:
        if self.cnpj and len(_only_digits(self.cnpj)) != 14:
            raise ValueError("cnpj deve ter 14 dígitos (com ou sem máscara)")
        if self.contact_email and "@" not in self.contact_email:
            raise ValueError("contact_email precisa ser um e-mail válido")
        if self.low_stock_threshold < 0:
            raise ValueError("low_stock_threshold não pode ser negativo")

    @property
    def cnpj_digits(self) -> str:
        """CNPJ normalizado (só dígitos) — vazio se ainda não preenchido."""
        return _only_digits(self.cnpj)
