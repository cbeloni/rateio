"""Registro de tentativas de autenticação."""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from config.database import get_session
from repository.base import Base


class Login(Base):
    __tablename__ = "login"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, nullable=True, index=True)
    email = Column(String(255), nullable=True)
    sucesso = Column(Boolean, nullable=False)
    data_hora = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    ip = Column(String(45), nullable=True)
    ip_encaminhado = Column(String(1024), nullable=True)
    user_agent = Column(String(512), nullable=True)
    idioma = Column(String(255), nullable=True)
    rota = Column(String(255), nullable=False, default="/login")
    motivo = Column(String(100), nullable=True)


def registrar_login(
    *,
    usuario_id: int | None,
    email: str | None,
    sucesso: bool,
    ip: str | None,
    ip_encaminhado: str | None,
    user_agent: str | None,
    idioma: str | None,
    motivo: str | None,
    rota: str = "/login",
) -> None:
    """Persiste uma tentativa de login sem armazenar a senha informada."""
    session = get_session()
    try:
        session.add(
            Login(
                usuario_id=usuario_id,
                email=email,
                sucesso=sucesso,
                ip=ip,
                ip_encaminhado=ip_encaminhado,
                user_agent=user_agent,
                idioma=idioma,
                motivo=motivo,
                rota=rota,
            )
        )
        session.commit()
    finally:
        session.close()
