"""Recursos compartilhados entre as rotas da API."""
from fastapi.templating import Jinja2Templates


class _CompatTemplates(Jinja2Templates):
    """Compatibiliza o uso antigo `TemplateResponse(nome, contexto)` com a API nova."""

    def TemplateResponse(self, name, context=None, *args, **kwargs):
        request = (context or {}).get("request")
        if request is None:
            raise ValueError("O contexto passado ao TemplateResponse deve conter 'request'.")
        return super().TemplateResponse(request, name, context, *args, **kwargs)


# Templates Jinja2 usados pelas rotas que renderizam páginas HTML
templates = _CompatTemplates(directory="templates")
