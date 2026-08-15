"""Módulo de API do Rateio Online.

Organiza todas as rotas da aplicação em sub-módulos dentro de ``api.rotas``.
"""
from .app import criar_app

__all__ = ["criar_app"]
