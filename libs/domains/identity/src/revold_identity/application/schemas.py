"""Schemas Pydantic que espelham products/ecommerce/contracts/api/identity.yaml."""
from __future__ import annotations

from pydantic import BaseModel


class LoginChallengeSchema(BaseModel):
    authorize_url: str
    state: str


class AuthenticatedUserSchema(BaseModel):
    external_id: str
    provider: str
    email: str
    name: str
    roles: list[str]


class StartLoginRequestSchema(BaseModel):
    redirect_uri: str


class CompleteLoginRequestSchema(BaseModel):
    code: str
    state: str


class IssueApiKeyRequestSchema(BaseModel):
    name: str


class IssuedApiKeySchema(BaseModel):
    key_id: str
    name: str
    raw_key: str
