"""Cliente do Azure SQL Database: engine, fábrica de sessão e a base declarativa do SQLAlchemy.

Não conhece nenhuma tabela nem nenhum domínio. Os modelos e os repositórios de cada contexto
moram na camada `adapters/azure_sql/` do domínio dono da porta e importam `Base` daqui.
"""

from revold_azure_sql.db import Base, get_session, make_engine, make_session_factory

__all__ = ["Base", "get_session", "make_engine", "make_session_factory"]
