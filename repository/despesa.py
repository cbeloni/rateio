from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, DECIMAL, Integer, String

from config.database import get_session
from repository.base import Base


class Despesa(Base):
    __tablename__ = "despesas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rateio_id = Column(Integer, nullable=False)
    mes = Column(String(255), nullable=False)
    ano = Column(Integer, nullable=False)
    categoria_id = Column(Integer, nullable=False)
    valor = Column(DECIMAL(10, 2), nullable=False, default=0)
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
            "mes": self.mes,
            "ano": self.ano,
            "categoria_id": self.categoria_id,
            "valor": float(self.valor or 0),
            "created_at": self.created_at,
        }


def upsert(rateio_id, mes, ano, categoria_id, valor):
    session = get_session()
    existing = (
        session.query(Despesa)
        .filter_by(rateio_id=rateio_id, mes=mes, ano=ano, categoria_id=categoria_id)
        .first()
    )
    if existing:
        existing.valor = valor
    else:
        existing = Despesa(
            rateio_id=rateio_id,
            mes=mes,
            ano=ano,
            categoria_id=categoria_id,
            valor=valor,
        )
        session.add(existing)
    session.commit()
    session.refresh(existing)
    result = existing.to_dict()
    session.close()
    return result


def listar_por_rateio_mes(rateio_id, mes, ano):
    session = get_session()
    registros = (
        session.query(Despesa)
        .filter_by(rateio_id=rateio_id, mes=mes, ano=ano)
        .all()
    )
    result = [r.to_dict() for r in registros]
    session.close()
    return result


def listar_por_rateio(rateio_id):
    session = get_session()
    registros = (
        session.query(Despesa)
        .filter(Despesa.rateio_id == rateio_id)
        .order_by(Despesa.ano.desc(), Despesa.id.asc())
        .all()
    )
    result = [r.to_dict() for r in registros]
    session.close()
    return result


def total_por_rateio_mes(rateio_id, mes, ano) -> Decimal:
    session = get_session()
    total = (
        session.query(Despesa)
        .filter_by(rateio_id=rateio_id, mes=mes, ano=ano)
        .all()
    )
    soma = sum((d.valor or Decimal("0")) for d in total)
    session.close()
    return soma
