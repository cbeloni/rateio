from datetime import datetime
import logging
from decimal import Decimal, ROUND_HALF_UP

from dto.fechamento_requests import get_transacao_credito
from repository.cota import listar_por_rateio as listar_cotas
from repository.credito_cota import total_por_destino as credito_por_destino
from repository.credito_cota import total_por_origem as credito_por_origem
from repository.despesa import total_por_rateio_mes
from repository.fechamento_cota import saldo_anterior, upsert as upsert_fechamento
from repository.membro import listar_por_rateio as listar_membros
from repository.extrato import ExtratoRepository
from repository.rateio import listar_todos
from service.rateio_service import cota_financiadora, valor_fundo_da_cota
from util.datas_uteis import meses_portugues


def fechar_pagamentos(data_inicial, data_final, rateio_id=None, mes=None, ano=None):
    logging.info(f"Fechando pagamentos de {data_inicial} até {data_final}")

    extrato_repository = ExtratoRepository()

    if mes is None or ano is None:
        mes = meses_portugues[datetime.strptime(data_inicial, "%d/%m/%Y").strftime("%B")]
        ano = datetime.strptime(data_inicial, "%d/%m/%Y").year

    rateios = listar_todos()
    if rateio_id is not None:
        rateios = [r for r in rateios if r["id"] == rateio_id]
    if not rateios:
        logging.warning("Nenhum rateio cadastrado; nenhum pagamento foi fechado.")
        return {"rateios": 0, "registros": 0, "dados": []}

    registros = []
    for rateio in rateios:
        rateio_id = rateio["id"]
        resultados = extrato_repository.consultar(data_inicial, data_final, rateio_id=rateio_id)
        cotas = listar_cotas(rateio_id, apenas_ativas=True)
        if not cotas:
            continue

        membros = listar_membros(rateio_id)
        identificadores_por_cota = {}
        for membro in membros:
            cota_id = membro["cota_id"]
            identificadores_por_cota.setdefault(cota_id, [])
            identificadores_por_cota[cota_id].extend(membro.get("identificadores_pagamento") or [])

        total_despesas = Decimal(total_por_rateio_mes(rateio_id, mes, ano))
        n_ativas = len(cotas)
        parcela = (
            (total_despesas / n_ativas).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if n_ativas
            else Decimal("0.00")
        )

        financiadora_id = cota_financiadora(rateio_id, rateio.get("organizador_id"))

        # Pagamentos reais casados do extrato.
        pagamentos_reais = {c["id"]: Decimal("0.00") for c in cotas}
        for resultado in resultados:
            if resultado.tipo_transacao != get_transacao_credito(resultado.banco):
                continue
            identificacao = (resultado.identificacao or "").lower()
            valor = Decimal(str(resultado.valor))

            # Qualquer pagamento de um membro é somado à cota correspondente.
            for cota in cotas:
                cota_id = cota["id"]
                termos = [t.lower() for t in identificadores_por_cota.get(cota_id, []) if t]
                if any(termo in identificacao for termo in termos):
                    pagamentos_reais[cota_id] += valor
                    break

        # Créditos movidos entre meses (mover saldo) e fundo por cota.
        creditos_recebidos = {}
        creditos_movidos = {}
        fundo = {}
        for cota in cotas:
            cota_id = cota["id"]
            creditos_recebidos[cota_id] = credito_por_destino(rateio_id, cota_id, mes, ano)
            creditos_movidos[cota_id] = credito_por_origem(rateio_id, cota_id, mes, ano)
            total_pagamento = pagamentos_reais[cota_id] + creditos_recebidos[cota_id]
            excesso = max(total_pagamento - parcela, Decimal("0.00"))
            limite = valor_fundo_da_cota(rateio, cota)
            fundo[cota_id] = min(excesso, limite).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        # Pagamentos: total do extrato + créditos recebidos de meses anteriores.
        pagamentos = {
            c["id"]: (pagamentos_reais[c["id"]] + creditos_recebidos[c["id"]]).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            for c in cotas
        }

        # Saldo acumulado por cota.
        saldos = {}
        for cota in cotas:
            cota_id = cota["id"]
            anterior = saldo_anterior(rateio_id, cota_id, excluir_mes=mes, excluir_ano=ano)
            if financiadora_id is not None and cota_id == financiadora_id:
                # A cota financiadora adiantou as despesas; os pagamentos das demais
                # cotas abatem o que ainda é devido a ela.
                pagamentos_outras = sum(
                    pagamentos_reais[outra] for outra in pagamentos_reais if outra != cota_id
                )
                total_atribuido = total_despesas - pagamentos_outras
            else:
                total_atribuido = pagamentos_reais[cota_id]
            saldos[cota_id] = (
                anterior
                + total_atribuido
                + creditos_recebidos[cota_id]
                - parcela
                - fundo[cota_id]
                - creditos_movidos[cota_id]
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        for cota in cotas:
            cota_id = cota["id"]
            registro = upsert_fechamento(
                rateio_id,
                cota_id,
                mes,
                ano,
                pagamentos[cota_id],
                fundo[cota_id],
                saldos[cota_id],
            )
            registros.append(registro)

    return {"rateios": len(rateios), "registros": len(registros), "dados": registros}


MESES_ORDEM = {
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
    "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12,
}


def _periodo_pagamentos_por_nome(mes, ano):
    """Retorna (data_inicial, data_final) do mês seguinte ao fechamento informado.

    Pagamentos do mês M são realizados no mês M+1.
    """
    import calendar

    numero = MESES_ORDEM.get(mes, 1)
    if numero == 12:
        mes_seguinte, ano_seguinte = 1, ano + 1
    else:
        mes_seguinte, ano_seguinte = numero + 1, ano
    ultimo_dia = calendar.monthrange(ano_seguinte, mes_seguinte)[1]
    data_inicial = f"01/{mes_seguinte:02d}/{ano_seguinte}"
    data_final = f"{ultimo_dia:02d}/{mes_seguinte:02d}/{ano_seguinte}"
    return data_inicial, data_final


def recalcular_fechamentos(rateio_id):
    """Recomputa todos os fechamentos do rateio em ordem cronológica.

    Deve ser chamado após movimentações de saldo entre meses, para que os meses
    de origem e destino reflitam os valores corretos.
    """
    from repository.despesa import listar_por_rateio as listar_despesas

    despesas = listar_despesas(rateio_id)
    meses_ano = sorted(
        {(d["mes"], d["ano"]) for d in despesas},
        key=lambda k: (k[1], MESES_ORDEM.get(k[0], 99)),
    )
    for mes, ano in meses_ano:
        data_inicial, data_final = _periodo_pagamentos_por_nome(mes, ano)
        fechar_pagamentos(data_inicial, data_final, rateio_id=rateio_id, mes=mes, ano=ano)
    return meses_ano
