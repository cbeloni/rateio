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
    rateios = montar_dashboard(usuario=usuario)
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "rateios": rateios,
            "usuario": usuario,
        },
    )
