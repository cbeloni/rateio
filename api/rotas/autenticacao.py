"""Rotas de autenticação e gestão de usuários (páginas web)."""
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request

from repository.usuario import (
    ativar_usuario,
    limpar_whatsapp_sessao,
    listar_usuarios,
    marcar_whatsapp_conectado,
    salvar_whatsapp_sessao,
)
from service.auth_service import (
    autenticar,
    criar_sessao,
    criar_usuario,
    destruir_sessao,
    enviar_email_confirmacao,
    exigir_login,
    gerar_token_confirmacao,
    usuario_atual,
    verificar_token_confirmacao,
)
from service.whatsapp_sessao_service import (
    WhatsAppBotError,
    criar_sessao as criar_sessao_whatsapp,
    excluir_sessao as excluir_sessao_whatsapp,
    obter_qrcode as obter_qrcode_whatsapp,
    obter_status as obter_status_whatsapp,
)

from ..dependencias import templates

logger = logging.getLogger(__name__)

router = APIRouter()


def _session_id_do_usuario(usuario: dict) -> str:
    """Identificador estável da sessão do usuário no whatsapp-bot."""
    return f"usuario_{usuario['id']}"


@router.get("/login", response_class=HTMLResponse)
async def pagina_login(request: Request):
    """Página de login."""
    if usuario_atual(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "usuario": None,
            "erro": None,
            "mensagem": request.query_params.get("mensagem", None),
        },
    )


@router.post("/login", response_class=HTMLResponse)
async def fazer_login(request: Request):
    """Processa o formulário de login."""
    form = await request.form()
    email = str(form.get("email", "")).strip().lower()
    senha = str(form.get("senha", ""))

    if not email or not senha:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "usuario": None,
                "erro": "Preencha todos os campos.",
                "mensagem": None,
            },
            status_code=400,
        )

    try:
        usuario = autenticar(email, senha)
    except ValueError as e:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "usuario": None,
                "erro": str(e),
                "mensagem": None,
            },
            status_code=401,
        )

    if not usuario:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "usuario": None,
                "erro": "E-mail ou senha inválidos.",
                "mensagem": None,
            },
            status_code=401,
        )

    criar_sessao(request, usuario["id"])
    return RedirectResponse(url="/", status_code=303)


@router.get("/cadastro", response_class=HTMLResponse)
async def pagina_cadastro(request: Request):
    """Página de cadastro de usuário."""
    if usuario_atual(request):
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse(
        "cadastro.html",
        {
            "request": request,
            "usuario": None,
            "erro": None,
            "nome": None,
            "email": None,
        },
    )


@router.post("/cadastro", response_class=HTMLResponse)
async def fazer_cadastro(request: Request):
    """Processa o formulário de cadastro de usuário."""
    form = await request.form()
    nome = str(form.get("nome", "")).strip()
    email = str(form.get("email", "")).strip().lower()
    senha = str(form.get("senha", ""))
    confirmar_senha = str(form.get("confirmar_senha", ""))

    if not nome or not email or not senha:
        return templates.TemplateResponse(
            "cadastro.html",
            {
                "request": request,
                "usuario": None,
                "erro": "Preencha todos os campos.",
                "nome": nome,
                "email": email,
            },
            status_code=400,
        )

    if len(senha) < 6:
        return templates.TemplateResponse(
            "cadastro.html",
            {
                "request": request,
                "usuario": None,
                "erro": "A senha deve ter no mínimo 6 caracteres.",
                "nome": nome,
                "email": email,
            },
            status_code=400,
        )

    if senha != confirmar_senha:
        return templates.TemplateResponse(
            "cadastro.html",
            {
                "request": request,
                "usuario": None,
                "erro": "As senhas não coincidem.",
                "nome": nome,
                "email": email,
            },
            status_code=400,
        )

    try:
        usuario = criar_usuario(nome=nome, email=email, senha=senha)
        token = gerar_token_confirmacao(usuario.id, usuario.email)
        base_url = str(request.base_url).rstrip("/")
        enviar_email_confirmacao(usuario, token, base_url)
    except ValueError as e:
        return templates.TemplateResponse(
            "cadastro.html",
            {
                "request": request,
                "usuario": None,
                "erro": str(e),
                "nome": nome,
                "email": email,
            },
            status_code=400,
        )
    except Exception:
        logging.error("Erro ao enviar email de confirmação", exc_info=True)

    return RedirectResponse(
        url="/login?mensagem=Cadastro realizado! Enviamos um link de confirmação para o seu e-mail.",
        status_code=303,
    )


@router.get("/confirmar-email/{token}")
async def confirmar_email(request: Request, token: str):
    """Confirma o e-mail do usuário usando o token enviado por e-mail."""
    dados = verificar_token_confirmacao(token)
    if not dados:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "usuario": None,
                "erro": "Link de confirmação inválido ou expirado. Faça um novo cadastro.",
                "mensagem": None,
            },
            status_code=400,
        )

    user_id = dados.get("user_id")
    usuario = ativar_usuario(user_id)
    if not usuario:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "usuario": None,
                "erro": "Usuário não encontrado.",
                "mensagem": None,
            },
            status_code=400,
        )

    return RedirectResponse(
        url="/login?mensagem=E-mail confirmado com sucesso! Agora você pode fazer login.",
        status_code=303,
    )


@router.get("/logout")
async def logout(request: Request):
    """Encerra a sessão do usuário."""
    destruir_sessao(request)
    return RedirectResponse(url="/", status_code=303)


@router.get("/configuracoes", response_class=HTMLResponse)
async def pagina_configuracoes(request: Request):
    """Página de configurações do usuário logado."""
    usuario = exigir_login(request)
    return templates.TemplateResponse(
        "perfil.html",
        {"request": request, "usuario": usuario},
    )


@router.get("/perfil", response_class=HTMLResponse)
async def pagina_perfil(request: Request):
    """Redireciona a rota antiga de perfil para as configurações."""
    return RedirectResponse(url="/configuracoes", status_code=303)


@router.post("/whatsapp/sessao")
async def whatsapp_criar_sessao(request: Request):
    """Cria (ou garante) a sessão de WhatsApp do usuário no bot."""
    usuario = exigir_login(request)
    session_id = _session_id_do_usuario(usuario)
    try:
        resultado = criar_sessao_whatsapp(session_id)
    except WhatsAppBotError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    salvar_whatsapp_sessao(usuario["id"], session_id)
    return {"session_id": session_id, **resultado}


@router.get("/whatsapp/sessao/qrcode")
async def whatsapp_obter_qrcode(request: Request):
    """Retorna o QR Code atual da sessão de WhatsApp do usuário."""
    usuario = exigir_login(request)
    session_id = usuario.get("whatsapp_session_id") or _session_id_do_usuario(usuario)
    try:
        resultado = obter_qrcode_whatsapp(session_id)
    except WhatsAppBotError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    conectado = bool(resultado.get("connected"))
    marcar_whatsapp_conectado(usuario["id"], conectado)
    return {"session_id": session_id, **resultado}


@router.get("/whatsapp/sessao/status")
async def whatsapp_obter_status(request: Request):
    """Retorna o status da sessão de WhatsApp do usuário."""
    usuario = exigir_login(request)
    session_id = usuario.get("whatsapp_session_id") or _session_id_do_usuario(usuario)
    try:
        resultado = obter_status_whatsapp(session_id)
    except WhatsAppBotError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    conectado = bool(resultado.get("connected"))
    marcar_whatsapp_conectado(usuario["id"], conectado)
    return {"session_id": session_id, **resultado}


@router.delete("/whatsapp/sessao")
async def whatsapp_excluir_sessao(request: Request):
    """Desconecta e remove a sessão de WhatsApp do usuário."""
    usuario = exigir_login(request)
    session_id = usuario.get("whatsapp_session_id")
    if session_id:
        try:
            excluir_sessao_whatsapp(session_id)
        except WhatsAppBotError as exc:
            logger.warning("Não foi possível encerrar a sessão no bot: %s", exc)

    limpar_whatsapp_sessao(usuario["id"])
    return {"success": True}


@router.get("/usuarios", response_class=HTMLResponse)
async def pagina_usuarios(request: Request):
    """Página de gerenciamento de usuários (apenas owners)."""
    usuario = exigir_login(request)
    if not usuario.get("owner"):
        return RedirectResponse(url="/", status_code=303)
    usuarios = listar_usuarios()
    return templates.TemplateResponse(
        "usuarios.html",
        {"request": request, "usuario": usuario, "usuarios": usuarios},
    )
