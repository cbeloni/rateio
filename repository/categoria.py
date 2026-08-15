from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String

from config.database import get_session
from repository.base import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rateio_id = Column(Integer, nullable=False)
    nome = Column(String(100), nullable=False)
    identificadores = Column(JSON, nullable=True)
    cor = Column(String(20), nullable=True)
    ordem = Column(Integer, nullable=False, default=0)
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
            "rateio_id": self.rateio_id,
            "nome": self.nome,
            "identificadores": self.identificadores or [],
            "cor": self.cor,
            "ordem": self.ordem,
            "ativo": bool(self.ativo),
            "created_at": self.created_at,
        }


def listar_por_rateio(rateio_id: int, apenas_ativas: bool = False):
    session = get_session()
    query = session.query(Categoria).filter(Categoria.rateio_id == rateio_id)
    if apenas_ativas:
        query = query.filter(Categoria.ativo.is_(True))
    categorias = query.order_by(Categoria.ordem.asc(), Categoria.id.asc()).all()
    result = [c.to_dict() for c in categorias]
    session.close()
    return result


def buscar_por_id(categoria_id: int):
    session = get_session()
    categoria = session.query(Categoria).filter(Categoria.id == categoria_id).first()
    session.close()
    return categoria


def buscar_por_nome(rateio_id: int, nome: str):
    session = get_session()
    categoria = (
        session.query(Categoria)
        .filter(Categoria.rateio_id == rateio_id, Categoria.nome == nome)
        .first()
    )
    session.close()
    return categoria
