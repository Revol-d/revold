"""Gate: o banco construído pelas migrações é igual ao que os modelos descrevem.

Os modelos (a "planta", em `adapters/postgres/` de cada domínio) e as migrações (o "diário da
obra", em `products/ecommerce/migrations/`) precisam bater. Quando não batem, o
`alembic revision --autogenerate` escreve a diferença como migração nova: medido em 2026-11-15,
antes deste teste, ele mandaria apagar 7 tabelas (o `env.py` só via o catálogo), 8 índices e 1
restrição de unicidade (criados pelas migrações e nunca declarados nos modelos).

O teste cria um banco vazio, aplica todas as migrações e pede ao Alembic a comparação com o
`metadata` do produto. Qualquer diferença reprova: mudou um modelo, escreva a migração no mesmo
PR (ou o contrário).

Precisa de um Postgres com pgvector em `DATABASE_URL_SYNC` e de permissão para criar banco. Sem
isso, pula, como os outros testes `integration`. No CI roda contra o Postgres do service.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from revold_ecommerce.adapters.database import metadata

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[3]
SERVER_URL = os.environ.get("DATABASE_URL_SYNC", "")


def _server_reachable() -> bool:
    if not SERVER_URL:
        return False
    try:
        with create_engine(SERVER_URL).connect():
            return True
    except Exception:  # noqa: BLE001 -- qualquer falha de conexão significa "sem banco": pula
        return False


@pytest.fixture
def empty_database(monkeypatch: pytest.MonkeyPatch):
    """Um banco novo e vazio no mesmo servidor, apagado no fim do teste."""
    if not _server_reachable():
        pytest.skip("Postgres não alcançável em DATABASE_URL_SYNC: pulando a conferência.")
    name = f"revold_schema_check_{uuid.uuid4().hex[:8]}"
    admin = create_engine(SERVER_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    url = make_url(SERVER_URL).set(database=name).render_as_string(hide_password=False)
    # O env.py das migrações lê o destino de DATABASE_URL_SYNC.
    monkeypatch.setenv("DATABASE_URL_SYNC", url)
    try:
        yield url
    finally:
        with admin.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": name},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


def _differences(url: str) -> list:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(conn, opts={"compare_type": True})
            return compare_metadata(context, metadata)
    finally:
        engine.dispose()


def test_migrations_build_exactly_what_the_models_describe(empty_database: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "products/ecommerce/migrations"))
    command.upgrade(config, "head")

    differences = _differences(empty_database)

    listing = "\n".join(f"  {difference}" for difference in differences)
    assert not differences, (
        "o banco migrado e os modelos divergem (o que o --autogenerate escreveria):\n"
        f"{listing}\n"
        "Mudou um modelo? Escreva a migração no mesmo PR. Mudou uma migração? Ajuste o modelo."
    )


def test_every_table_in_the_database_has_a_model() -> None:
    """O teste acima só vê o que está no `metadata`: domínio com tabela fora dele passaria calado."""
    expected = {
        "ai_assistant_product_index",
        "catalog_categories",
        "catalog_product_variants",
        "catalog_products",
        "identity_api_keys",
        "inventory_stock_levels",
        "order_lines",
        "orders",
        "payment_charges",
        "store_settings",
    }
    assert expected <= set(
        metadata.tables
    ), f"faltam no metadata: {expected - set(metadata.tables)}"
