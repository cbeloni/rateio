"""Routers da API organizados por domínio."""
from fastapi import APIRouter

from . import autenticacao, consultas, gestao, paginas, processamento

api_router = APIRouter()
api_router.include_router(paginas.router)
api_router.include_router(autenticacao.router)
api_router.include_router(consultas.router)
api_router.include_router(processamento.router)
api_router.include_router(gestao.router)

__all__ = ["api_router"]
