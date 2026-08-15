"""Fábrica da aplicação FastAPI."""
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from repository.base import criar_tabelas_rateio
from repository.extrato import criar_tabela_extrato
from repository.usuario import criar_tabela_usuarios

from .rotas import api_router

SECRET_KEY = "rateio_online_secret_key_2026_change_me"


def _registrar_handlers(app: FastAPI) -> None:
    """Trata erros não capturados: retorna detalhe + stacktrace.

    Em requisições AJAX (formulários enviados via fetch) o erro é devolvido em
    JSON para ser exibido no modal de feedback. Em navegação normal, devolve uma
    página HTML com o stacktrace colapsado.
    """
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        tb = traceback.format_exc()
        detail = str(exc) or exc.__class__.__name__
        is_ajax = (request.headers.get("x-requested-with") or "").lower() == "xmlhttprequest"
        if is_ajax:
            return JSONResponse(status_code=500, content={"detail": detail, "traceback": tb})
        return HTMLResponse(
            "<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'>"
            "<title>Erro interno</title></head><body style='font-family:Arial'>"
            f"<h1>Ocorreu um erro</h1><p>{detail}</p>"
            "<details><summary>Ver stacktrace completo</summary>"
            f"<pre style='white-space:pre-wrap;word-break:break-word;background:#f5f5f5;padding:10px'>{tb}</pre>"
            "</details></body></html>",
            status_code=500,
        )


def criar_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI com os routers e middleware."""
    app = FastAPI()

    # Middleware de sessão para autenticação
    app.add_middleware(
        SessionMiddleware,
        secret_key=SECRET_KEY,
        same_site="lax",
    )

    app.include_router(api_router)

    _registrar_handlers(app)

    # Criar a tabela de usuários ao iniciar
    try:
        criar_tabela_usuarios()
    except Exception:
        pass

    # Criar as tabelas do modelo de rateio ao iniciar
    try:
        criar_tabelas_rateio()
    except Exception:
        pass

    # Criar a tabela de extrato ao iniciar
    try:
        criar_tabela_extrato()
    except Exception:
        pass

    return app
