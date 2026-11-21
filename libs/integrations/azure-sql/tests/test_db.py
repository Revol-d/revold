"""O cliente do Azure SQL monta engine e sessão a partir da URL recebida, sem abrir conexão."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from revold_azure_sql.db import Base, make_engine, make_session_factory

_URL = (
    "mssql+aioodbc://user:secret@db.example:1433/shop"
    "?driver=ODBC+Driver+17+for+SQL+Server"
)


def test_make_engine_uses_the_url_it_receives() -> None:
    engine = make_engine(_URL)

    assert isinstance(engine, AsyncEngine)
    assert engine.url.host == "db.example"
    assert engine.url.database == "shop"


def test_engine_hides_the_password_when_printed() -> None:
    assert "secret" not in str(make_engine(_URL).url)


def test_session_factory_is_bound_to_the_engine_and_keeps_objects_after_commit() -> None:
    engine = make_engine(_URL)

    session = make_session_factory(engine)()

    assert isinstance(session, AsyncSession)
    assert session.bind is engine
    # expire_on_commit=False: os repositórios commitam e devolvem o objeto de domínio depois.
    assert session.sync_session.expire_on_commit is False


def test_base_is_the_declarative_base_the_domain_models_inherit_from() -> None:
    assert issubclass(Base, DeclarativeBase)
