from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Column, DateTime, DECIMAL, Integer, String

from config.database import get_session
from repository.base import Base


class Rateio(Base):
    __tablename__ = "rateios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organizador_id = Column(Integer, nullable=False)
    nome = Column(String(255), nullable=False)
    descricao = Column(String(255), nullable=True)
    valor_fundo_padrao = Column(DECIMAL(10, 2), nullable=False, default=Decimal("0.00"))
    valor_inicial_caixa = Column(DECIMAL(10, 2), nullable=False, default=Decimal("0.00"))
    dia_fechamento = Column(Integer, nullable=False, default=0)
    pluggy_client_id = Column(String(255), nullable=True)
    pluggy_client_secret = Column(String(255), nullable=True)
    pluggy_account_id = Column(String(255), nullable=True)
    ativo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def save(self):
        session = get_session()
        session.add(self)
        session.commit()
        session.refresh(self)
        result = self.to_dict()
        session.close()
        return result

    def to_dict(self):
        return {
            "id": self.id,
            "organizador_id": self.organizador_id,
            "nome": self.nome,
            "descricao": self.descricao,
            "valor_fundo_padrao": float(self.valor_fundo_padrao) if self.valor_fundo_padrao is not None else None,
            "valor_inicial_caixa": float(self.valor_inicial_caixa) if self.valor_inicial_caixa is not None else None,
            "dia_fechamento": self.dia_fechamento,
            "pluggy_client_id": self.pluggy_client_id,
            "pluggy_client_secret": self.pluggy_client_secret,
            "pluggy_account_id": self.pluggy_account_id,
            "ativo": bool(self.ativo),
            "created_at": self.created_at,
        }


def listar_por_organizador(organizador_id: int):
    session = get_session()
    rateios = (
        session.query(Rateio)
        .filter(Rateio.organizador_id == organizador_id, Rateio.ativo.is_(True))
        .order_by(Rateio.id.asc())
        .all()
    )
    result = [r.to_dict() for r in rateios]
    session.close()
    return result


def listar_por_membro(usuario_id: int):
    """Rateios onde o usuário é membro de alguma cota."""
    from repository.cota import Cota
    from repository.membro import Membro

    session = get_session()
    membros = (
        session.query(Membro)
        .filter(Membro.usuario_id == usuario_id, Membro.ativo.is_(True))
        .all()
    )
    cota_ids = [m.cota_id for m in membros]
    if not cota_ids:
        session.close()
        return []

    cotas = session.query(Cota).filter(Cota.id.in_(cota_ids), Cota.ativo.is_(True)).all()
    rateio_ids = {c.rateio_id for c in cotas}
    if not rateio_ids:
        session.close()
        return []

    rateios = (
        session.query(Rateio)
        .filter(Rateio.id.in_(rateio_ids), Rateio.ativo.is_(True))
        .order_by(Rateio.id.asc())
        .all()
    )
    result = [r.to_dict() for r in rateios]
    session.close()
    return result


def listar_todos():
    session = get_session()
    rateios = (
        session.query(Rateio)
        .filter(Rateio.ativo.is_(True))
        .order_by(Rateio.id.asc())
        .all()
    )
    result = [r.to_dict() for r in rateios]
    session.close()
    return result


def buscar_por_id(rateio_id: int):
    session = get_session()
    rateio = session.query(Rateio).filter(Rateio.id == rateio_id).first()
    session.close()
    return rateio


def buscar_por_nome(nome: str):
    session = get_session()
    rateio = session.query(Rateio).filter(Rateio.nome == nome).first()
    session.close()
    return rateio


def desativar(rateio_id: int):
    """Exclusão lógica do rateio (marca como inativo, preservando os dados)."""
    session = get_session()
    try:
        rateio = session.query(Rateio).filter(Rateio.id == rateio_id).first()
        if rateio:
            rateio.ativo = False
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
