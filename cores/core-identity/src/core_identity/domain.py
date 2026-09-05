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
