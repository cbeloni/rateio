from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, DECIMAL, Integer, String

from config.database import get_session
from repository.base import Base


class CreditoCota(Base):
    """Crédito movido de um mês para o seguinte, abatido no QR de cobrança."""

    __tablename__ = "creditos_cota"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rateio_id = Column(Integer, nullable=False)
    cota_id = Column(Integer, nullable=False)
    origem_mes = Column(String(255), nullable=False)
    origem_ano = Column(Integer, nullable=False)
    destino_mes = Column(String(255), nullable=False)
    destino_ano = Column(Integer, nullable=False)
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
            "cota_id": self.cota_id,
            "origem_mes": self.origem_mes,
            "origem_ano": self.origem_ano,
            "destino_mes": self.destino_mes,
            "destino_ano": self.destino_ano,
            "valor": float(self.valor or 0),
            "created_at": self.created_at,
        }


def mover(rateio_id, cota_id, origem_mes, origem_ano, destino_mes, destino_ano, valor):
    """Registra a movimentação de um saldo excedente para o mês seguinte.

    Se já existir um crédito para a mesma origem/destino, apenas atualiza o valor.
    """
    session = get_session()
    existing = (
        session.query(CreditoCota)
        .filter_by(
            rateio_id=rateio_id,
            cota_id=cota_id,
            origem_mes=origem_mes,
            origem_ano=origem_ano,
            destino_mes=destino_mes,
            destino_ano=destino_ano,
        )
        .first()
    )
    if existing:
        existing.valor = valor
        session.commit()
        session.refresh(existing)
        result = existing.to_dict()
        session.close()
        return result

    credito = CreditoCota(
        rateio_id=rateio_id,
        cota_id=cota_id,
        origem_mes=origem_mes,
        origem_ano=origem_ano,
        destino_mes=destino_mes,
        destino_ano=destino_ano,
        valor=valor,
    )
    session.add(credito)
    session.commit()
    session.refresh(credito)
    result = credito.to_dict()
    session.close()
    return result


def total_por_destino(rateio_id, cota_id, mes, ano) -> Decimal:
    """Soma dos créditos movidos para a cota no mês de destino informado."""
    session = get_session()
    registros = (
        session.query(CreditoCota)
        .filter_by(rateio_id=rateio_id, cota_id=cota_id, destino_mes=mes, destino_ano=ano)
        .all()
    )
    total = sum((r.valor or Decimal("0")) for r in registros)
    session.close()
    return Decimal(str(total))


def total_por_origem(rateio_id, cota_id, mes, ano) -> Decimal:
    """Soma dos créditos movidos a partir do mês de origem informado."""
    session = get_session()
    registros = (
        session.query(CreditoCota)
        .filter_by(rateio_id=rateio_id, cota_id=cota_id, origem_mes=mes, origem_ano=ano)
        .all()
    )
    total = sum((r.valor or Decimal("0")) for r in registros)
    session.close()
    return Decimal(str(total))


def listar_por_rateio(rateio_id):
    session = get_session()
    registros = (
        session.query(CreditoCota)
        .filter(CreditoCota.rateio_id == rateio_id)
        .order_by(CreditoCota.id.desc())
        .all()
    )
    result = [r.to_dict() for r in registros]
    session.close()
    return result
