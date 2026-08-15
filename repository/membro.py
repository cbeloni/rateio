from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, DECIMAL, Integer, JSON, String

from config.database import get_session
from repository.base import Base


class Membro(Base):
    __tablename__ = "membros"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cota_id = Column(Integer, nullable=False)
    usuario_id = Column(Integer, nullable=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    telefone = Column(String(50), nullable=True)
    identificadores_pagamento = Column(JSON, nullable=True)
    principal = Column(Boolean, nullable=False, default=False)
    receber_mensagens = Column(Boolean, nullable=False, default=True)
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
            "cota_id": self.cota_id,
            "usuario_id": self.usuario_id,
            "nome": self.nome,
            "email": self.email,
            "telefone": self.telefone,
            "identificadores_pagamento": self.identificadores_pagamento or [],
            "principal": bool(self.principal),
            "receber_mensagens": bool(self.receber_mensagens),
            "ativo": bool(self.ativo),
            "created_at": self.created_at,
        }


def listar_por_cota(cota_id: int):
    session = get_session()
    membros = (
        session.query(Membro)
        .filter(Membro.cota_id == cota_id)
        .order_by(Membro.id.asc())
        .all()
    )
    result = [m.to_dict() for m in membros]
    session.close()
    return result


def listar_por_rateio(rateio_id: int):
    """Membros de todas as cotas de um rateio."""
    from repository.cota import listar_por_rateio as listar_cotas

    cotas = listar_cotas(rateio_id)
    ids = [c["id"] for c in cotas]
    if not ids:
        return []

    session = get_session()
    membros = (
        session.query(Membro)
        .filter(Membro.cota_id.in_(ids), Membro.ativo.is_(True))
        .all()
    )
    result = [m.to_dict() for m in membros]
    session.close()
    return result


def membro_contato(cota_id: int):
    """Retorna o primeiro membro ativo com e-mail ou telefone para contato (ou None)."""
    session = get_session()
    membros = (
        session.query(Membro)
        .filter(Membro.cota_id == cota_id, Membro.ativo.is_(True))
        .order_by(Membro.id.asc())
        .all()
    )
    session.close()
    for membro in membros:
        if membro.email or membro.telefone:
            return membro
    return membros[0] if membros else None


def buscar_por_id(membro_id: int):
    session = get_session()
    membro = session.query(Membro).filter(Membro.id == membro_id).first()
    session.close()
    return membro
