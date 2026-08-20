"""Rotas de processamento e operações (JSON)."""
from datetime import datetime

from fastapi import APIRouter

from dto.cobrar_request import CobrarRequest
from dto.email import EmailRequest
from dto.extrato_request import ExtratoApiRequest
from dto.fechamento_requests import (
    FechamentoDespesasRequest,
    FechamentoPagamentosDate,
    FechamentoRequest,
)
from dto.pagbank_request import MovimentosPagbankParams
from dto.pix import PixRequest
from dto.resumo_requests import ResumoRequest
from service.cobrar_service import (
    cobrar_e_enviar_email,
    cobrar_e_enviar_whatsapp,
    pode_enviar_cobranca,
)
from service.dashboard import montar_dashboard
from service.email_service import enviar_email
from service.extrato.extrato_abstract import ExtratoAbstract
from service.extrato.factory_extrato import factory_extrato_service
from service.fechamento_despesas import fechar_despesas
from service.fechamento_pagamento import fechar_pagamentos
from service.message_whatsapp import montar_messagem_whatsapp
from service.qrcode_service import generate_qrcode
from service.resumo import consultar_tipo_transacao
from service.send_whatsapp import send_whatsapp_message
from util.datas_uteis import meses_portugues

router = APIRouter()


@router.post("/extrato")
def extrato(request: ExtratoApiRequest = None, rateio_id: int | None = None) -> dict:
    if request is None:
        request = ExtratoApiRequest()

    if request.provider == "pluggy":
        return _extrato_pluggy(request, rateio_id)

    extrato: ExtratoAbstract = factory_extrato_service(request.provider)
    extrato_dados = extrato.obter_extrato(request.data_inicial, request.data_final)
    if request.gravar:
        extrato.gravar_extrato(extrato_dados)
    return extrato_dados


def _extrato_pluggy(request: ExtratoApiRequest, rateio_id: int | None = None) -> dict:
    """Importa o extrato Pluggy por rateio, usando as credenciais de cada um."""
    from repository.rateio import buscar_por_id, listar_todos
    from service.extrato.pluggy import ExtratoPluggyService

    if rateio_id:
        rateio = buscar_por_id(rateio_id)
        rateios = [rateio.to_dict()] if rateio else []
    else:
        rateios = listar_todos()

    resultado = {"rateios": []}
    for rateio in rateios:
        if not rateio.get("pluggy_client_id") or not rateio.get("pluggy_client_secret"):
            continue

        service = ExtratoPluggyService(
            client_id=rateio["pluggy_client_id"],
            client_secret=rateio["pluggy_client_secret"],
            account_id=rateio.get("pluggy_account_id"),
            rateio_id=rateio["id"],
        )
        dados = service.obter_extrato(request.data_inicial, request.data_final)
        if request.gravar:
            service.gravar_extrato(dados)
        resultado["rateios"].append({"rateio_id": rateio["id"], "dados": dados})

    return resultado


@router.post("/fechamento-despesas")
def fechamento_despesas(request: FechamentoDespesasRequest = None) -> dict:
    if request is None:
        request = FechamentoDespesasRequest()
    return fechar_despesas(**request.model_dump())


@router.post("/fechamento-pagamentos")
def fechamento_pagamentos(request: FechamentoRequest = None) -> dict:
    if request is None:
        request = FechamentoPagamentosDate()
    # Quando vem da cron (sem body), FechamentoPagamentosDate já entrega o
    # mes/ano do fechamento (mês anterior ao corrente). Em chamadas manuais
    # com body, mes/ano ficam None e são derivados de data_inicial.
    return fechar_pagamentos(
        request.data_inicial,
        request.data_final,
        mes=getattr(request, "mes", None),
        ano=getattr(request, "ano", None),
    )


@router.post("/qrcode")
def qrcode(
    request: PixRequest = PixRequest(
        name_receiver="Cauê Beloni",
        city_receiver="Santo André",
        key="cbeloni@gmail.com",
        identification="12345",
        zipcode_receiver="09291250",
        description="rateio mensal",
        amount=1.0,
    ),
) -> dict:
    return generate_qrcode(request)


@router.post("/send-email")
def send_email(request: EmailRequest) -> dict:
    enviar_email(request.subject, request.body, request.recipient)
    return {"message": "Email sent successfully"}


@router.post("/send-whatsapp")
def send_whatsapp(numero: str = "5511941503226") -> dict:
    rateios = montar_dashboard()
    mensagens = montar_messagem_whatsapp(rateios)
    for mensagem in mensagens:
        send_whatsapp_message(numero, mensagem)
    return {"message": "Mensagens enviadas com sucesso"}


def _cobranca_request_padrao() -> CobrarRequest:
    """Fluxo da cron: cobra o mês fechado no último dia (mês anterior ao atual).

    O fechamento de despesas + QRCodes ocorre no último dia do mês às 23h;
    o envio da cobrança no dia 1 deve mirar esse mês recém-fechado.
    """
    hoje = datetime.now()  # pyright: ignore  (naive, consistente com o restante do projeto)
    if hoje.month == 1:
        mes_num, ano = 12, hoje.year - 1
    else:
        mes_num, ano = hoje.month - 1, hoje.year
    return CobrarRequest(
        mes=meses_portugues[datetime(ano, mes_num, 1).strftime("%B")],  # pyright: ignore
        ano=str(ano),
    )


@router.post("/cobrar")
def cobrar(request: CobrarRequest = None) -> dict:
    if request is None:
        request = _cobranca_request_padrao()
    if not pode_enviar_cobranca():
        return {
            "message": "Cobrança só pode ser enviada às 9h do dia 1",
            "enviado": False,
            "bloqueado": True,
        }
    cobrar_e_enviar_email(request)
    return {"message": "Email sent successfully", "mes": request.mes, "ano": request.ano}


@router.post("/cobrar-whatsapp")
def cobrar_whatsapp(request: CobrarRequest = None) -> dict:
    if request is None:
        request = _cobranca_request_padrao()
    if not pode_enviar_cobranca():
        return {
            "message": "Cobrança só pode ser enviada às 9h do dia 1",
            "enviado": False,
            "bloqueado": True,
        }
    cobrar_e_enviar_whatsapp(request)
    return {"message": "WhatsApp messages sent successfully", "mes": request.mes, "ano": request.ano}


@router.post("/resumo")
def resumo(request: ResumoRequest = None):
    if request is None:
        request = ResumoRequest()
    return consultar_tipo_transacao(request)


@router.post("/movimentos-pagbank")
def movimentos_pagbank(request: MovimentosPagbankParams):
    from integrations.pagbank import consultar_movimentos_pagbank

    response = consultar_movimentos_pagbank(
        data_movimento=request.data_movimento,
        page_number=request.page_number,
        page_size=request.page_size,
        tipo_movimento=request.tipo_movimento,
    )

    if response is None:
        return {"error": "Erro ao consultar movimentos PagBank"}

    return {"status_code": response.status_code, "data": response.json()}
