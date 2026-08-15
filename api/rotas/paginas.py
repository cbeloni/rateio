"""Rotas de páginas (HTML)."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from service.auth_service import usuario_atual
from service.dashboard import montar_dashboard

from ..dependencias import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def read_home(request: Request):
    usuario = usuario_atual(request)
    if not usuario:
        # Visitante não autenticado: mostra a landing page.
        return templates.TemplateResponse(
            "landing.html",
            {"request": request, "usuario": None},
        )

    # Usuário logado: mostra apenas os rateios que ele organiza ou participa.
    rateios = montar_dashboard(usuario=usuario)
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "rateios": rateios,
            "usuario": usuario,
        },
    )
