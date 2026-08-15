from fastapi.templating import Jinja2Templates

from dto.cobrar_request import CobrarRequest
from repository.cobranca import (
    Cobranca,
    buscar_por_cota,
    cobrancas_pendentes,
    marcar_status,
    marcar_status_whatsapp,
)
from repository.membro import membro_contato
from service.email_service import enviar_email
from service.whatsapp_service import enviar_cobranca_whatsapp


def _membro_responsavel(cobranca):
    """Retorna o membro responsável pela cota da cobrança (ou None)."""
    if cobranca.cota_id:
        membro = membro_contato(cobranca.cota_id)
        if membro:
            return membro
    return None


def _enviar_email(cobranca) -> bool:
    """Envia a cobrança por e-mail e registra o status no canal e-mail."""
    templates = Jinja2Templates(directory="templates")
    context = {
        "request": {},
        "mes": cobranca.mes,
        "valor": cobranca.valor,
        "codigo_pix": cobranca.brcode,
        "imagem_url": f"https://br-se1.magaluobjects.com/qrcodepix/{cobranca.url_qrcode}",
    }
    body = templates.env.get_template("email.html").render(**context)
    assunto = f'Cobrança {cobranca.cota} - {cobranca.mes}.{cobranca.ano}'

    membro = _membro_responsavel(cobranca)
    email = membro.email if membro and membro.email else 'cbeloni@gmail.com'

    try:
        enviar_email(subject=assunto, body=body, to_email=email)
        marcar_status(mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='enviado')
        return True
    except Exception:
        marcar_status(mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='falha')
        return False


def cobrar_e_enviar_email(fechamento_request: CobrarRequest):
    # Envio em lote: só cobra cotas ainda pendentes (evita duplicidade).
    cobrancas = cobrancas_pendentes(
        mes=fechamento_request.mes,
        ano=fechamento_request.ano,
        filtro=Cobranca.status == 'pendente',
    )

    for cobranca in cobrancas:
        _enviar_email(cobranca)


def _enviar_whatsapp(cobranca) -> bool:
    """Envia a cobrança por WhatsApp e registra o status no canal WhatsApp."""
    templates = Jinja2Templates(directory="templates")
    context = {
        "request": {},
        "cota": cobranca.cota,
        "mes": cobranca.mes,
        "valor": cobranca.valor,
        "codigo_pix": cobranca.brcode,
    }

    body = templates.env.get_template("whatsapp_template.txt").render(**context)

    membro = _membro_responsavel(cobranca)
    telefone = membro.telefone if membro else None
    if not telefone:
        marcar_status_whatsapp(
            mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='falha'
        )
        return False

    try:
        enviar_cobranca_whatsapp(
            telefone=telefone,
            mensagem=body,
            imagem_url=f"https://br-se1.magaluobjects.com/qrcodepix/{cobranca.url_qrcode}",
            pix_code=cobranca.brcode,
        )
        marcar_status_whatsapp(
            mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='enviado'
        )
        return True
    except Exception:
        marcar_status_whatsapp(
            mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='falha'
        )
        return False


def cobrar_e_enviar_whatsapp(fechamento_request: CobrarRequest):
    # Envio em lote: só cobra cotas ainda pendentes (evita duplicidade).
    cobrancas = cobrancas_pendentes(
        mes=fechamento_request.mes,
        ano=fechamento_request.ano,
        filtro=Cobranca.notificacao_whatsapp == 'pendente',
    )

    for cobranca in cobrancas:
        _enviar_whatsapp(cobranca)


def cobrar_cota(mes, ano, cota_id) -> dict:
    """Dispara a cobrança de uma cota: e-mail sempre, WhatsApp se disponível.

    Envio individual (botão "Cobrar"): NÃO valida se a mensagem já foi enviada
    antes, permitindo reenviar para a cota quantas vezes for necessário.

    Retorna os canais utilizados: {"encontrada", "email", "whatsapp"}.
    """
    cobranca = buscar_por_cota(mes, ano, cota_id)
    if not cobranca:
        return {"encontrada": False, "email": False, "whatsapp": False}

    email_ok = _enviar_email(cobranca)
    whatsapp_ok = _enviar_whatsapp(cobranca)

    return {"encontrada": True, "email": email_ok, "whatsapp": whatsapp_ok}
