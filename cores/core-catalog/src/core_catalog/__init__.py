"""core-catalog: bounded context de catálogo de produtos.

Este core não conhece FastAPI, SQLAlchemy nem nenhum detalhe de infraestrutura.
Ele define entidades de domínio, portas (interfaces) e casos de uso. Quem
implementa as portas são os adapters (ver adapters/persistence).
"""
