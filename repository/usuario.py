from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from config.database import get_session
from datetime import datetime

Base = declarative_base()

PERFIS = {"organizador", "membro"}


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    senha_hash = Column(String(512), nullable=False)
    perfil = Column(String(20), nullable=False, default="membro")
    ativo = Column(Boolean, nullable=False, default=False)
    owner = Column(Boolean, nullable=False, default=False)
    whatsapp_session_id = Column(String(64), nullable=True)
    whatsapp_conectado = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def save(self):
        session = get_session()
        session.add(self)
        session.commit()
        session.refresh(self)
        return self.to_dict()

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "perfil": self.perfil,
            "ativo": self.ativo,
            "owner": bool(self.owner),
            "whatsapp_session_id": self.whatsapp_session_id,
            "whatsapp_conectado": bool(self.whatsapp_conectado),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def criar_tabela_usuarios():
    """Cria a tabela de usuários caso ainda não exista."""
    from sqlalchemy import inspect

    session = get_session()
    engine = session.get_bind()
    if not inspect(engine).has_table("usuarios"):
        Base.metadata.create_all(engine)
    else:
        # Verificar se a coluna 'ativo' existe; se não, adicionar
        columns = [col["name"] for col in inspect(engine).get_columns("usuarios")]
        if "ativo" not in columns:
            from sqlalchemy import text

            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN ativo BOOLEAN NOT NULL DEFAULT FALSE"))
        if "owner" not in columns:
            from sqlalchemy import text

            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN owner BOOLEAN NOT NULL DEFAULT FALSE"))
        if "whatsapp_session_id" not in columns:
            from sqlalchemy import text

            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN whatsapp_session_id VARCHAR(64) NULL"))
        if "whatsapp_conectado" not in columns:
            from sqlalchemy import text

            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE usuarios ADD COLUMN whatsapp_conectado BOOLEAN NOT NULL DEFAULT FALSE"))
    session.close()


def buscar_por_email(email: str):
    session = get_session()
    usuario = session.query(Usuario).filter(Usuario.email == email).first()
    session.close()
    return usuario


def buscar_por_id(user_id: int):
    session = get_session()
    usuario = session.query(Usuario).filter(Usuario.id == user_id).first()
    session.close()
    return usuario


def listar_usuarios():
    session = get_session()
    usuarios = session.query(Usuario).order_by(Usuario.id.asc()).all()
    result = [u.to_dict() for u in usuarios]
    session.close()
    return result


def ativar_usuario(user_id: int):
    """Ativa o usuário após confirmação de email."""
    session = get_session()
    usuario = session.query(Usuario).filter(Usuario.id == user_id).first()
    if usuario:
        usuario.ativo = True
        session.commit()
        session.refresh(usuario)
        result = usuario.to_dict()
        session.close()
        return result
    session.close()
    return None


def salvar_whatsapp_sessao(user_id: int, session_id: str) -> dict | None:
    """Vincula uma sessão do WhatsApp (whatsapp-bot) ao usuário."""
    session = get_session()
    usuario = session.query(Usuario).filter(Usuario.id == user_id).first()
    if not usuario:
        session.close()
        return None
    usuario.whatsapp_session_id = session_id
    usuario.whatsapp_conectado = False
    session.commit()
    session.refresh(usuario)
    result = usuario.to_dict()
    session.close()
    return result


def marcar_whatsapp_conectado(user_id: int, conectado: bool) -> dict | None:
    """Atualiza o cache de status de conexão do WhatsApp do usuário."""
    session = get_session()
    usuario = session.query(Usuario).filter(Usuario.id == user_id).first()
    if not usuario:
        session.close()
        return None
    usuario.whatsapp_conectado = bool(conectado)
    session.commit()
    session.refresh(usuario)
    result = usuario.to_dict()
    session.close()
    return result


def limpar_whatsapp_sessao(user_id: int) -> dict | None:
    """Remove o vínculo da sessão de WhatsApp do usuário."""
    session = get_session()
    usuario = session.query(Usuario).filter(Usuario.id == user_id).first()
    if not usuario:
        session.close()
        return None
    usuario.whatsapp_session_id = None
    usuario.whatsapp_conectado = False
    session.commit()
    session.refresh(usuario)
    result = usuario.to_dict()
    session.close()
    return result
