"""Fábrica da aplicação FastAPI."""
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from repository.base import criar_tabelas_rateio
from repository.extrato import criar_tabela_extrato
from repository.usuario import criar_tabela_usuarios

from .rotas import api_router

SECRET_KEY = "rateio_online_secret_key_2026_change_me"


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
