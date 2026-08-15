"""Base declarativa compartilhada pelos repositórios do módulo rateio."""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def criar_tabelas_rateio(engine=None):
    """Cria as tabelas do modelo de rateio caso ainda não existam.

    As alterações de esquema (colunas etc.) são gerenciadas pelo Alembic
    (``alembic upgrade head``, executado antes do app subir).
    """
    # Importa os modelos para registrá-los no metadata compartilhado.
    from repository import categoria as _categoria  # noqa: F401
    from repository import classificacao_manual as _classificacao_manual  # noqa: F401
    from repository import cobranca as _cobranca  # noqa: F401
    from repository import cota as _cota  # noqa: F401
    from repository import credito_cota as _credito_cota  # noqa: F401
    from repository import despesa as _despesa  # noqa: F401
    from repository import fechamento_cota as _fechamento_cota  # noqa: F401
    from repository import membro as _membro  # noqa: F401
    from repository import rateio as _rateio  # noqa: F401
    from repository import responsabilidade as _responsabilidade  # noqa: F401

    if engine is None:
        from config.database import criar_engine

        engine = criar_engine()

    Base.metadata.create_all(engine)
