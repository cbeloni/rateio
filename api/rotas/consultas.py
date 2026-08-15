"""Rotas de consulta de dados (JSON)."""
from fastapi import APIRouter

from repository.despesa import listar_por_rateio as despesas_do_rateio
from repository.fechamento_cota import listar_por_rateio as fechamentos_do_rateio
from repository.rateio import listar_todos
from service.dashboard import montar_dashboard
from service.drive_service import get_last_file_from_drive
from service.email_service import read_emails_from_gmail

router = APIRouter()


def _todas_despesas() -> list:
    dados = []
    for rateio in listar_todos():
        dados.extend(despesas_do_rateio(rateio["id"]))
    return dados


def _todos_fechamentos() -> list:
    dados = []
    for rateio in listar_todos():
        dados.extend(fechamentos_do_rateio(rateio["id"]))
    return dados


@router.get("/about")
def about() -> dict[str, str]:
    return {"message": "This is the about page."}


@router.get("/mail")
def mail() -> list:
    return read_emails_from_gmail()


@router.get("/drive")
def drive() -> list:
    return get_last_file_from_drive()


@router.get("/despesas")
def despesas() -> list:
    return _todas_despesas()


@router.get("/caixa")
def caixa() -> list:
    return _todos_fechamentos()


@router.get("/concialiacao")
def concialiacao() -> list:
    return montar_dashboard()
