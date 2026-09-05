"""core-inventory: bounded context de controle de estoque (PENDENTE).

Escopo previsto: ajuste de estoque por variante (SKU), reserva de estoque
durante o checkout manual, RBAC de quem pode alterar estoque (papel STAFF/
ADMIN de core_identity.domain.Role). Depende de core-catalog (para os SKUs)
e core-identity (para RBAC) já existirem, o que já é o caso.
"""
