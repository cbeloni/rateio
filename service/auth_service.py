import hashlib
import os

from dotenv import dotenv_values, load_dotenv
from fastapi import HTTPException, Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from repository.membro import vincular_por_email
from repository.usuario import Usuario, buscar_por_email, buscar_por_id

load_dotenv()
_config = dotenv_values(".env")

SESSION_COOKIE_NAME = "rateio_online_session"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 dias

# Serializer para tokens de confirmação de email
SECRET_KEY = _config.get("SECRET_KEY") or "rateio_online_secret_key_2026_change_me"
serializer = URLSafeTimedSerializer(SECRET_KEY, salt="email-confirmation")


def hash_senha(senha: str, salt: bytes | None = None) -> tuple[str, str]:
    """Gera um hash seguro da senha usando PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt,
        100_000,
    )
    return hash_bytes.hex(), salt.hex()


def verificar_senha(senha: str, senha_hash: str, salt_hex: str) -> bool:
    """Verifica se a senha informada corresponde ao hash armazenado."""
    salt = bytes.fromhex(salt_hex)
    hash_calculado = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        salt,
        100_000,
    ).hex()
    return hash_calculado == senha_hash


def criar_usuario(nome: str, email: str, senha: str) -> Usuario:
    """Cria um novo usuário com senha criptografada (organizador, inativo)."""
    if buscar_por_email(email):
        raise ValueError("Já existe um usuário com este e-mail.")

    senha_hash, salt = hash_senha(senha)
    usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=f"{salt}:{senha_hash}",
        perfil="organizador",
        ativo=False,
    )
    usuario.save()
    return usuario


def gerar_token_confirmacao(user_id: int, email: str) -> str:
    """Gera um token assinado para confirmação de email (válido por 24h)."""
    return serializer.dumps({"user_id": user_id, "email": email})


def verificar_token_confirmacao(token: str) -> dict | None:
    """Verifica o token de confirmação. Retorna dados do usuário se válido, senão None."""
    try:
        dados = serializer.loads(token, max_age=86400)  # 24 horas
        return dados
    except (SignatureExpired, BadSignature):
        return None


def enviar_email_confirmacao(usuario: Usuario, token: str, base_url: str = "http://localhost:8000") -> None:
    """Envia email de confirmação de cadastro."""
    from service.email_service import enviar_email

    link_confirmacao = f"{base_url}/confirmar-email/{token}"

    subject = "Confirme seu cadastro - Rateio Online"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f7ef; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; padding: 30px; border: 1px solid #d9e4d3;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="color: #124e32; font-size: 24px; margin: 0;">Rateio Online</h1>
                <p style="color: #5b6b61; margin: 5px 0 0;">Confirmação de cadastro</p>
            </div>
            <hr style="border: none; border-top: 1px solid #d9e4d3; margin: 20px 0;">
            <p style="color: #1c2b21; font-size: 16px;">Olá, <b>{usuario.nome}</b>!</p>
            <p style="color: #1c2b21; font-size: 16px;">
                Seu cadastro no Rateio Online foi criado com sucesso. Para ativar sua conta,
                clique no botão abaixo para confirmar seu endereço de e-mail.
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{link_confirmacao}" style="background-color: #1f6f4a; color: #ffffff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-size: 16px; font-weight: bold; display: inline-block;">
                    Confirmar e-mail
                </a>
            </div>
            <p style="color: #5b6b61; font-size: 14px;">
                Se o botão acima não funcionar, copie e cole o link abaixo no seu navegador:
            </p>
            <p style="color: #1f6f4a; font-size: 13px; word-break: break-all;">{link_confirmacao}</p>
            <p style="color: #5b6b61; font-size: 13px; margin-top: 20px;">
                Este link expira em <b>24 horas</b>.
            </p>
            <hr style="border: none; border-top: 1px solid #d9e4d3; margin: 20px 0;">
            <p style="color: #5b6b61; font-size: 12px; text-align: center; margin: 0;">
                Se você não criou uma conta no Rateio Online, ignore este e-mail.
            </p>
        </div>
    </body>
    </html>
    """

    enviar_email(subject, body, usuario.email)


def autenticar(email: str, senha: str) -> dict | None:
    """Autentica um usuário. Retorna os dados do usuário se válido, senão None."""
    usuario = buscar_por_email(email)
    if not usuario:
        return None

    if not usuario.ativo:
        raise ValueError("Conta não ativada. Verifique seu e-mail para confirmar o cadastro.")

    try:
        salt_hex, senha_hash = usuario.senha_hash.split(":", 1)
    except ValueError:
        return None

    if verificar_senha(senha, senha_hash, salt_hex):
        vincular_por_email(usuario.email, usuario.id)
        return usuario.to_dict()
    return None


def criar_sessao(request: Request, user_id: int) -> None:
    """Cria a sessão de autenticação armazenando o ID do usuário num cookie."""
    request.session["user_id"] = user_id


def destruir_sessao(request: Request) -> None:
    """Remove a sessão de autenticação."""
    request.session.clear()


def usuario_atual(request: Request) -> dict | None:
    """Retorna os dados do usuário logado, ou None se não autenticado."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    usuario = buscar_por_id(user_id)
    if not usuario:
        return None
    return usuario.to_dict()


def exigir_login(request: Request) -> dict:
    """Protege uma rota: redireciona para /login se não autenticado."""
    usuario = usuario_atual(request)
    if not usuario:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return usuario


def exigir_perfil(request: Request, perfis_permitidos: set[str]) -> dict:
    """Protege uma rota por perfil: exige login e perfil autorizado."""
    usuario = usuario_atual(request)
    if not usuario:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    if usuario["perfil"] not in perfis_permitidos:
        raise HTTPException(
            status_code=403,
            detail="Você não tem permissão para acessar esta página.",
        )
    return usuario
