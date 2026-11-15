from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# As unidades do monorepo já estão instaladas no ambiente (workspace uv): não é preciso
# mexer no sys.path. Este arquivo é de quem opera o banco, fora do `src/` de qualquer
# unidade, e por isso lê DATABASE_URL_SYNC direto do ambiente.
#
# O metadata com as tabelas de TODOS os domínios. Antes só o catálogo era registrado, e o
# --autogenerate concluía que as outras tabelas sobravam e mandava apagá-las.
from revold_ecommerce.adapters.database import metadata as target_metadata

config = context.config
# O `fileConfig` desliga todos os loggers que já existem no processo. Na linha de comando isso
# não importa; dentro do pytest (o teste que confere as migrações), os testes que leem log
# depois dele passavam a ver o log vazio. Quem chama o Alembic por código pede para não mexer.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)


db_url = os.environ.get("DATABASE_URL_SYNC")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
