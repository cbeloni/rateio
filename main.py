"""Entry point da aplicação.

Todas as rotas estão organizadas no módulo ``api``.
Execução: ``uvicorn main:app --reload``
"""
from api import criar_app

app = criar_app()