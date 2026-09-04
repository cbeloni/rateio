"""Configuração do ambiente de migração Alembic.

Usa o metadata dos modelos SQLAlchemy da aplicação e a conexão configurada em
``.env`` (via ``config.database``). O histórico é registrado na tabela
``migrations``.
"""
from logging.config import fileConfig

from sqlalchemy import create_engine

from alembic import context

# Importa os modelos para registrá-los no metadata compartilhado.
from repository import (  # noqa: F401
    categoria,
    classificacao_manual,
    cobranca,
    cota,
    credito_cota,
    despesa,
    fechamento_cota,
    membro,
    login,
    rateio,
    responsabilidade,
)
from repository.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    from config.database import _config

    return (
        f"mysql+mysqlconnector://{_config['USER']}:{_config['PASSWORD']}"
        f"@{_config['HOST']}/{_config['DATABASE']}"
    )


def run_migrations_offline() -> None:
    """Executa as migrações em modo offline (sem conexão real)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="migrations",
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa as migrações em modo online (conexão real)."""
    connectable = create_engine(_database_url(), pool_pre_ping=True)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="migrations",
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
