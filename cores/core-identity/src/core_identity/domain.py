from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    CUSTOMER = "customer"
    STAFF = "staff"
    ADMIN = "admin"


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Identidade resolvida a partir de um provedor federado (nunca uma senha)."""

    external_id: str
    provider: str
    email: str
    name: str
    roles: tuple[Role, ...] = (Role.CUSTOMER,)

    def has_role(self, role: Role) -> bool:
        return role in self.roles


@dataclass(slots=True)
class LoginChallenge:
    """Dados necessários para o frontend redirecionar o usuário ao provedor."""

    authorize_url: str
    state: str


@dataclass(frozen=True, slots=True)
class ApiKeyPrincipal:
    """Identidade de um chamador de API externo (parceiro/integração),
    resolvida a partir de uma API key — nunca de sessão de navegador (ver
    ADR-0016). Só carrega o que a exposição pública de API precisa saber
    sobre quem está chamando; nunca o segredo em si."""

    key_id: str
    name: str


class ApiKeyNotFound(Exception):
    def __init__(self, key_id: str) -> None:
        super().__init__(f"API key não encontrada: {key_id}")
        self.key_id = key_id
