from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from config.database import get_session
from repository.base import Base


class Cota(Base):
    __tablename__ = "cotas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rateio_id = Column(Integer, nullable=False)
    identificador = Column(String(50), nullable=False)
    descricao = Column(String(50), nullable=True)
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
            "identificador": self.identificador,
            "descricao": self.descricao,
            "ordem": self.ordem,
            "ativo": self.ativo,
            "created_at": self.created_at,
        }


def listar_por_rateio(rateio_id: int, apenas_ativas: bool = False):
    session = get_session()
    query = session.query(Cota).filter(Cota.rateio_id == rateio_id)
    if apenas_ativas:
        query = query.filter(Cota.ativo.is_(True))
    cotas = query.order_by(Cota.ordem.asc(), Cota.id.asc()).all()
    result = [c.to_dict() for c in cotas]
    session.close()
    return result


def buscar_por_id(cota_id: int):
    session = get_session()
    cota = session.query(Cota).filter(Cota.id == cota_id).first()
    session.close()
    return cota


def buscar_por_identificador(rateio_id: int, identificador: str):
    session = get_session()
    cota = (
        session.query(Cota)
        .filter(Cota.rateio_id == rateio_id, Cota.identificador == identificador)
        .first()
    )
    session.close()
    return cota
