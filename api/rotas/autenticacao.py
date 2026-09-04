"""Rotas de autenticação e gestão de usuários (páginas web)."""
import logging

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request

from repository.usuario import ativar_usuario, listar_usuarios
from repository.login import registrar_login
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

from ..dependencias import templates

router = APIRouter()


def _registrar_tentativa_login(request: Request, **dados) -> None:
    """Registra a tentativa sem deixar a auditoria impedir o fluxo de login."""
    cliente = request.client
    try:
        registrar_login(
            ip=cliente.host if cliente else None,
            ip_encaminhado=request.headers.get("x-forwarded-for"),
            user_agent=request.headers.get("user-agent"),
            idioma=request.headers.get("accept-language"),
            rota=request.url.path,
            **dados,
        )
    except Exception:
        logging.exception("Não foi possível registrar a tentativa de login")


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
        _registrar_tentativa_login(
            request,
            usuario_id=None,
            email=email or None,
            sucesso=False,
            motivo="campos_obrigatorios",
        )
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
        _registrar_tentativa_login(
            request,
            usuario_id=None,
            email=email,
            sucesso=False,
            motivo="conta_inativa",
        )
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
        _registrar_tentativa_login(
            request,
            usuario_id=None,
            email=email,
            sucesso=False,
            motivo="credenciais_invalidas",
        )
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

    _registrar_tentativa_login(
        request,
        usuario_id=usuario["id"],
        email=email,
        sucesso=True,
        motivo="autenticado",
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


@router.get("/perfil", response_class=HTMLResponse)
async def pagina_perfil(request: Request):
    """Página do perfil do usuário logado."""
    usuario = exigir_login(request)
    return templates.TemplateResponse(
        "perfil.html",
        {"request": request, "usuario": usuario},
    )


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
