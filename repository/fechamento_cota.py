from datetime import datetime
from decimal import Decimal

from sqlalchemy import Column, DateTime, DECIMAL, Integer, String

from config.database import get_session
from repository.base import Base

MESES_ORDEM = {
    "Janeiro": 1,
    "Fevereiro": 2,
    "Março": 3,
    "Abril": 4,
    "Maio": 5,
    "Junho": 6,
    "Julho": 7,
    "Agosto": 8,
    "Setembro": 9,
    "Outubro": 10,
    "Novembro": 11,
    "Dezembro": 12,
}


class FechamentoCota(Base):
    __tablename__ = "fechamentos_cota"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rateio_id = Column(Integer, nullable=False)
    cota_id = Column(Integer, nullable=False)
    mes = Column(String(255), nullable=False)
    ano = Column(Integer, nullable=False)
    pagamentos = Column(DECIMAL(10, 2), nullable=False, default=0)
    fundo = Column(DECIMAL(10, 2), nullable=False, default=0)
    saldo = Column(DECIMAL(10, 2), nullable=False, default=0)
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
            "mes": self.mes,
            "ano": self.ano,
            "pagamentos": float(self.pagamentos or 0),
            "fundo": float(self.fundo or 0),
            "saldo": float(self.saldo or 0),
            "created_at": self.created_at,
        }


def upsert(rateio_id, cota_id, mes, ano, pagamentos, fundo, saldo):
    session = get_session()
    existing = (
        session.query(FechamentoCota)
        .filter_by(rateio_id=rateio_id, cota_id=cota_id, mes=mes, ano=ano)
        .first()
    )
    if existing:
        existing.pagamentos = pagamentos
        existing.fundo = fundo
        existing.saldo = saldo
    else:
        existing = FechamentoCota(
            rateio_id=rateio_id,
            cota_id=cota_id,
            mes=mes,
            ano=ano,
            pagamentos=pagamentos,
            fundo=fundo,
            saldo=saldo,
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
        session.query(FechamentoCota)
        .filter_by(rateio_id=rateio_id, mes=mes, ano=ano)
        .all()
    )
    result = [r.to_dict() for r in registros]
    session.close()
    return result


def listar_por_rateio(rateio_id):
    session = get_session()
    registros = (
        session.query(FechamentoCota)
        .filter(FechamentoCota.rateio_id == rateio_id)
        .order_by(FechamentoCota.ano.desc(), FechamentoCota.id.asc())
        .all()
    )
    result = [r.to_dict() for r in registros]
    session.close()
    return result


def saldo_anterior(rateio_id, cota_id, excluir_mes=None, excluir_ano=None) -> Decimal:
    """Retorna o saldo do mês imediatamente anterior ao período informado.

    Considera apenas meses cronologicamente anteriores ao mês informado. Assim,
    ao sincronizar um mês isolado (ex.: Janeiro), o saldo anterior vem do mês
    anterior (ou zero), e nunca de meses futuros — evitando "saldo excedente"
    incorreto em meses com pagamento menor que a parcela.
    """
    session = get_session()
    registros = (
        session.query(FechamentoCota)
        .filter(
            FechamentoCota.rateio_id == rateio_id,
            FechamentoCota.cota_id == cota_id,
        )
        .all()
    )
    session.close()

    if excluir_mes is not None and excluir_ano is not None:
        ordem_atual = MESES_ORDEM.get(excluir_mes, 0)
        registros = [
            r for r in registros
            if (r.ano or 0) < excluir_ano
            or ((r.ano or 0) == excluir_ano and MESES_ORDEM.get(r.mes, 0) < ordem_atual)
        ]

    if not registros:
        return Decimal("0.00")

    registros.sort(
        key=lambda r: (r.ano or 0, MESES_ORDEM.get(r.mes, 0), r.id or 0),
        reverse=True,
    )
    return Decimal(str(registros[0].saldo or 0))
