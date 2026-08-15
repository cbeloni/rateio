from datetime import datetime

from sqlalchemy import Column, DateTime, DECIMAL, Integer

from config.database import get_session
from repository.base import Base


class Responsabilidade(Base):
    """Categoria da qual um membro é responsável pelo pagamento."""

    __tablename__ = "responsabilidades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rateio_id = Column(Integer, nullable=False)
    membro_id = Column(Integer, nullable=False)
    categoria_id = Column(Integer, nullable=False)
    valor = Column(DECIMAL(10, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "rateio_id": self.rateio_id,
            "membro_id": self.membro_id,
            "categoria_id": self.categoria_id,
            "valor": float(self.valor) if self.valor is not None else None,
        }


def listar_por_rateio(rateio_id):
    session = get_session()
    registros = (
        session.query(Responsabilidade)
        .filter(Responsabilidade.rateio_id == rateio_id)
        .all()
    )
    result = [r.to_dict() for r in registros]
    session.close()
    return result


def listar_por_membro(membro_id):
    session = get_session()
    registros = (
        session.query(Responsabilidade)
        .filter(Responsabilidade.membro_id == membro_id)
        .all()
    )
    result = [r.to_dict() for r in registros]
    session.close()
    return result


def substituir_do_membro(rateio_id, membro_id, categoria_ids):
    """Substitui as categorias de responsabilidade do membro pelos ids informados."""
    session = get_session()
    session.query(Responsabilidade).filter(
        Responsabilidade.membro_id == membro_id
    ).delete()
    for cid in categoria_ids:
        try:
            cid_int = int(cid)
        except (TypeError, ValueError):
            continue
        session.add(
            Responsabilidade(
                rateio_id=rateio_id, membro_id=membro_id, categoria_id=cid_int
            )
        )
    session.commit()
    session.close()
