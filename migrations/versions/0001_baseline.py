"""Baseline: cria as tabelas base caso ainda não existam.

Usa ``create_all`` (checkfirst) do próprio metadata da aplicação. Em bancos que
já possuem as tabelas, é um no-op; em bancos novos, cria tudo antes das
migrações de coluna seguintes.
"""
from alembic import op

# Garante que todos os modelos estejam registrados no metadata compartilhado.
from repository import (  # noqa: F401
    categoria,
    classificacao_manual,
    cobranca,
    cota,
    credito_cota,
    despesa,
    fechamento_cota,
    membro,
    rateio,
    responsabilidade,
)
from repository.base import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    Base.metadata.drop_all(bind=op.get_bind())
