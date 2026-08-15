from sqlalchemy import Column, Integer, String, DECIMAL, Text
from config.database import get_session
from util.datas_uteis import normalizar_data_mysql

from repository.base import Base


class Cobranca(Base):
    __tablename__ = "cobrancas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mes = Column(String(255), nullable=False)
    ano = Column(Integer, nullable=False)
    cota = Column(String(255))
    cota_id = Column(Integer, nullable=True)
    valor = Column(DECIMAL(10, 2))
    qrcode = Column(Text)
    brcode = Column(String(1024))
    url_qrcode = Column(String(255))
    status = Column(String(50), default="pendente")
    notificacao_whatsapp = Column(String(50), default="pendente")
    data_atual = Column(String(50), nullable=True)

    def save(self):
        session = get_session()
        existing_record = session.query(Cobranca).filter_by(mes=self.mes, ano=self.ano, cota=self.cota).first()
        if existing_record:
            session.delete(existing_record)
            session.commit()

        data_atual = normalizar_data_mysql(self.data_atual)

        nova_cobranca = Cobranca(
            mes=self.mes,
            ano=self.ano,
            cota=self.cota,
            cota_id=self.cota_id,
            valor=self.valor,
            qrcode=self.qrcode,
            brcode=self.brcode,
            url_qrcode=self.url_qrcode,
            status=self.status,
            notificacao_whatsapp=self.notificacao_whatsapp,
            data_atual=data_atual,
        )
        session.add(nova_cobranca)
        session.commit()

    def to_dict(self):
        return {
            "id": self.id,
            "mes": self.mes,
            "ano": self.ano,
            "cota": self.cota,
            "cota_id": self.cota_id,
            "valor": self.valor,
            "qrcode": self.qrcode,
            "brcode": self.brcode,
            "url_qrcode": self.url_qrcode,
            "status": self.status,
            "notificacao_whatsapp": self.notificacao_whatsapp,
        }


def cobrancas_pendentes(mes, ano, filtro):
    session = get_session()
    return session.query(Cobranca).filter_by(mes=mes, ano=ano).filter(filtro).all()


def cobrancas_status(mes, ano, status, cota):
    session = get_session()
    return session.query(Cobranca).filter_by(mes=mes, ano=ano, status=status, cota=cota).all()


def get_last_cobranca() -> Cobranca:
    session = get_session()
    return session.query(Cobranca).order_by(Cobranca.id.desc()).first()


def marcar_status(mes, ano, cota, status):
    session = get_session()
    record = session.query(Cobranca).filter_by(mes=mes, ano=ano, cota=cota).first()
    if record:
        record.status = status
        session.commit()


def marcar_status_whatsapp(mes, ano, cota, status):
    session = get_session()
    record = session.query(Cobranca).filter_by(mes=mes, ano=ano, cota=cota).first()
    if record:
        record.notificacao_whatsapp = status
        session.commit()


def listar_por_cotas(cota_ids):
    """Lista as cobranças das cotas informadas (mais recentes primeiro)."""
    if not cota_ids:
        return []
    session = get_session()
    registros = (
        session.query(Cobranca)
        .filter(Cobranca.cota_id.in_(cota_ids))
        .order_by(Cobranca.id.desc())
        .all()
    )
    result = [r.to_dict() for r in registros]
    session.close()
    return result


def buscar_por_cota(mes, ano, cota_id):
    """Busca a cobrança de uma cota em um mês/ano específico (ou None)."""
    session = get_session()
    registro = session.query(Cobranca).filter_by(mes=mes, ano=ano, cota_id=cota_id).first()
    session.close()
    return registro
