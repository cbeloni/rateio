from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from config.database import get_session
from repository.base import Base


class ClassificacaoManual(Base):
    __tablename__ = "classificacao_manual"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rateio_id = Column(Integer, nullable=False)
    codigo_transacao = Column(String(255), nullable=False)
    categoria_id = Column(Integer, nullable=False)
    usuario_id = Column(Integer, nullable=True)
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
            "rateio_id": self.rateio_id,
            "codigo_transacao": self.codigo_transacao,
            "categoria_id": self.categoria_id,
            "usuario_id": self.usuario_id,
            "created_at": self.created_at,
        }


def buscar_por_codigo(rateio_id: int, codigo_transacao: str):
    session = get_session()
    registro = (
        session.query(ClassificacaoManual)
        .filter(
            ClassificacaoManual.rateio_id == rateio_id,
            ClassificacaoManual.codigo_transacao == codigo_transacao,
        )
        .first()
    )
    session.close()
    return registro


def listar_por_rateio(rateio_id: int):
    session = get_session()
    registros = (
        session.query(ClassificacaoManual)
        .filter(ClassificacaoManual.rateio_id == rateio_id)
        .order_by(ClassificacaoManual.id.desc())
        .all()
    )
    result = [r.to_dict() for r in registros]
    session.close()
    return result


def salvar(rateio_id, codigo_transacao, categoria_id, usuario_id=None):
    session = get_session()
    existing = (
        session.query(ClassificacaoManual)
        .filter_by(rateio_id=rateio_id, codigo_transacao=codigo_transacao)
        .first()
    )
    if existing:
        existing.categoria_id = categoria_id
        existing.usuario_id = usuario_id
    else:
        existing = ClassificacaoManual(
            rateio_id=rateio_id,
            codigo_transacao=codigo_transacao,
            categoria_id=categoria_id,
            usuario_id=usuario_id,
        )
        session.add(existing)
    session.commit()
    session.refresh(existing)
    result = existing.to_dict()
    session.close()
    return result


def remover(rateio_id: int, codigo_transacao: str):
    session = get_session()
    registro = (
        session.query(ClassificacaoManual)
        .filter_by(rateio_id=rateio_id, codigo_transacao=codigo_transacao)
        .first()
    )
    if registro:
        session.delete(registro)
        session.commit()
    session.close()
