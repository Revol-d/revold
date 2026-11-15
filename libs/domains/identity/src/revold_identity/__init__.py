"""`identity`: bounded context de identidade e sessão.

Por decisão de arquitetura (ADR-0003), este core nunca armazena senha.
Toda autenticação é delegada a um IdentityProvider externo (federado).
"""
