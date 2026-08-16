import logging

from fastapi.templating import Jinja2Templates

from dto.cobrar_request import CobrarRequest
from repository.cobranca import (
    Cobranca,
    cobrancas_pendentes,
    listar_por_cota_mes,
    marcar_status,
    marcar_status_whatsapp,
)
from repository.membro import buscar_por_id, membro_contato
from service.email_service import enviar_email
from service.whatsapp_service import enviar_cobranca_whatsapp

logger = logging.getLogger(__name__)


def _membro_responsavel(cobranca):
    """Retorna o membro responsável pela cobrança (membro_id) ou o contato da cota."""
    if cobranca.membro_id:
        membro = buscar_por_id(cobranca.membro_id)
        if membro:
            return membro
    if cobranca.cota_id:
        membro = membro_contato(cobranca.cota_id)
        if membro:
            return membro
    return None


def _membro_optou_nao_receber(membro) -> bool:
    """Verifica a flag de consentimento `receber_mensagens`.

    Esta é a única porta de entrada para o envio: deve ser checada SEMPRE,
    em todos os canais (e-mail e WhatsApp).

    - Membro inexistente (None) => False (não é "opt-out", segue o fluxo normal).
    - Flag `False` ou `None`    => True (tratado como "não quer receber").
    """
    if membro is None:
        return False
    return not bool(membro.receber_mensagens)


def _enviar_email(cobranca) -> bool:
    """Envia a cobrança por e-mail e registra o status no canal e-mail."""
    logger.info(
        "E-MAIL [início] preparando cobrança: cota=%s, %s/%s, valor=R$ %s, membro_id=%s",
        cobranca.cota, cobranca.mes, cobranca.ano, cobranca.valor, cobranca.membro_id,
    )

    membro = _membro_responsavel(cobranca)
    if _membro_optou_nao_receber(membro):
        logger.info(
            "Membro %s optou por não receber mensagens — e-mail não enviado (%s %s/%s).",
            membro.nome, cobranca.cota, cobranca.mes, cobranca.ano,
        )
        marcar_status(mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='nao_enviar', membro_id=cobranca.membro_id)
        return False

    email = membro.email if membro and membro.email else 'cbeloni@gmail.com'
    logger.info(
        "E-MAIL [início] destinatário=%s, cota=%s, %s/%s, valor=R$ %s",
        email, cobranca.cota, cobranca.mes, cobranca.ano, cobranca.valor,
    )

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
    logger.info(
        "E-MAIL [meio] mensagem renderizada: assunto=%r, corpo=%d caracteres — enviando para %s",
        assunto, len(body), email,
    )

    try:
        enviar_email(subject=assunto, body=body, to_email=email)
        marcar_status(mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='enviado', membro_id=cobranca.membro_id)
        logger.info(
            "E-MAIL [fim] enviado com sucesso para %s (%s %s/%s).",
            email, cobranca.cota, cobranca.mes, cobranca.ano,
        )
        return True
    except Exception:
        logger.exception(
            "E-MAIL [fim] falha ao enviar para %s (%s %s/%s).",
            email, cobranca.cota, cobranca.mes, cobranca.ano,
        )
        marcar_status(mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='falha', membro_id=cobranca.membro_id)
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
    logger.info(
        "WHATSAPP [início] preparando cobrança: cota=%s, %s/%s, valor=R$ %s, membro_id=%s",
        cobranca.cota, cobranca.mes, cobranca.ano, cobranca.valor, cobranca.membro_id,
    )

    membro = _membro_responsavel(cobranca)
    if _membro_optou_nao_receber(membro):
        logger.info(
            "Membro %s optou por não receber mensagens — WhatsApp não enviado (%s %s/%s).",
            membro.nome, cobranca.cota, cobranca.mes, cobranca.ano,
        )
        marcar_status_whatsapp(
            mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='nao_enviar', membro_id=cobranca.membro_id
        )
        return False

    telefone = membro.telefone if membro else None
    if not telefone:
        logger.warning(
            "Cobrança %s %s/%s sem telefone para WhatsApp (membro_id=%s).",
            cobranca.cota, cobranca.mes, cobranca.ano, cobranca.membro_id,
        )
        marcar_status_whatsapp(
            mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='falha', membro_id=cobranca.membro_id
        )
        return False

    logger.info(
        "WHATSAPP [início] destinatário=%s, cota=%s, %s/%s, valor=R$ %s",
        telefone, cobranca.cota, cobranca.mes, cobranca.ano, cobranca.valor,
    )

    templates = Jinja2Templates(directory="templates")
    context = {
        "request": {},
        "cota": cobranca.cota,
        "mes": cobranca.mes,
        "valor": cobranca.valor,
        "codigo_pix": cobranca.brcode,
    }
    body = templates.env.get_template("whatsapp_template.txt").render(**context)
    logger.info(
        "WHATSAPP [meio] mensagem renderizada: %d caracteres — enviando para %s",
        len(body), telefone,
    )

    try:
        enviar_cobranca_whatsapp(
            telefone=telefone,
            mensagem=body,
            imagem_url=f"https://br-se1.magaluobjects.com/qrcodepix/{cobranca.url_qrcode}",
            pix_code=cobranca.brcode,
        )
        marcar_status_whatsapp(
            mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='enviado', membro_id=cobranca.membro_id
        )
        logger.info(
            "WHATSAPP [fim] enviado com sucesso para %s (%s %s/%s).",
            telefone, cobranca.cota, cobranca.mes, cobranca.ano,
        )
        return True
    except Exception:
        logger.exception(
            "WHATSAPP [fim] falha ao enviar para %s (%s %s/%s).",
            telefone, cobranca.cota, cobranca.mes, cobranca.ano,
        )
        marcar_status_whatsapp(
            mes=cobranca.mes, ano=cobranca.ano, cota=cobranca.cota, status='falha', membro_id=cobranca.membro_id
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

    Com QRs por membro, envia uma cobrança para cada cobranca da cota.

    Retorna os canais utilizados: {"encontrada", "email", "whatsapp"}.
    """
    cobrancas = listar_por_cota_mes(mes, ano, cota_id)
    if not cobrancas:
        logger.warning("Cobrança não encontrada: cota_id=%s mes=%s ano=%s", cota_id, mes, ano)
        return {"encontrada": False, "email": False, "whatsapp": False}

    email_ok = False
    whatsapp_ok = False
    for cobranca in cobrancas:
        # E-mail e WhatsApp são independentes: uma falha no WhatsApp (bot fora
        # do ar) não pode impedir o envio do e-mail, e vice-versa.
        try:
            email_ok = _enviar_email(cobranca) or email_ok
        except Exception:
            logger.exception("Erro inesperado ao enviar e-mail da cobrança id=%s.", cobranca.id)
        try:
            whatsapp_ok = _enviar_whatsapp(cobranca) or whatsapp_ok
        except Exception:
            logger.exception("Erro inesperado ao enviar WhatsApp da cobrança id=%s.", cobranca.id)

    logger.info(
        "Cobrança da cota %s (%s/%s): encontrada=True, email=%s, whatsapp=%s",
        cota_id, mes, ano, email_ok, whatsapp_ok,
    )
    return {"encontrada": True, "email": email_ok, "whatsapp": whatsapp_ok}
