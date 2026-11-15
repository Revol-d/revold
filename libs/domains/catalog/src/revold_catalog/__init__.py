"""Domínio de catálogo de produtos (bounded context).

As camadas `domain/`, `ports/` e `application/` não conhecem FastAPI,
SQLAlchemy nem nenhum detalhe de infraestrutura: definem entidades, portas
(interfaces) e casos de uso. Quem implementa as portas é a camada
`adapters/` deste mesmo pacote (`adapters/postgres`, `adapters/media`).
"""
