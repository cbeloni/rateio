import logging

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from dto.fechamento_requests import get_transacao_debito
from repository.categoria import listar_por_rateio as listar_categorias
from repository.classificacao_manual import listar_por_rateio as listar_classificacao
from repository.cobranca import cobrancas_status
from repository.cota import listar_por_rateio as listar_cotas
from repository.despesa import upsert as upsert_despesa
from repository.extrato import ExtratoRepository
from repository.membro import listar_por_rateio as listar_membros
from repository.rateio import listar_todos
from service.drive_service import get_last_file_from_drive
from service.qrcode_service import gerar_salvar_qrcode
from service.rateio_service import cota_financiadora, valor_fundo_da_cota
from util.datas_uteis import meses_portugues, normalizar_data_mysql, ultimo_dia_mes_atual


def fechar_despesas(data_inicial, data_final, valida_mes, gerar_cobranca=True, rateio_id=None):
    get_last_file_from_drive()

    extrato_repository = ExtratoRepository()

    mes = meses_portugues[datetime.strptime(data_inicial, "%d/%m/%Y").strftime("%B")]
    ano = datetime.strptime(data_inicial, "%d/%m/%Y").year

    rateios = listar_todos()
    if rateio_id is not None:
        rateios = [r for r in rateios if r["id"] == rateio_id]
    if not rateios:
        logging.warning("Nenhum rateio cadastrado; nenhuma despesa foi fechada.")
        return {"rateios": 0, "registros": 0, "dados": []}

    registros = []
    for rateio in rateios:
        rateio_id = rateio["id"]
        resultados = extrato_repository.consultar(data_inicial, data_final, rateio_id=rateio_id)
        categorias = listar_categorias(rateio_id, apenas_ativas=True)
        cotas = listar_cotas(rateio_id, apenas_ativas=True)
        if not categorias or not cotas:
            continue

        # Periodicidade: 0 = último dia do mês; 1..31 = dia específico.
        dia = rateio.get("dia_fechamento") or 0
        dia_do_fechamento = ultimo_dia_mes_atual().day if dia == 0 else dia
        pode_gerar_qrcode = not valida_mes or datetime.now().day == dia_do_fechamento

        classificacoes = {
            c["codigo_transacao"]: c["categoria_id"]
            for c in listar_classificacao(rateio_id)
        }

        totais = {c["id"]: Decimal("0.00") for c in categorias}
        for resultado in resultados:
            if resultado.tipo_transacao != get_transacao_debito(resultado.banco):
                continue

            codigo = resultado.codigo_transacao
            if codigo and codigo in classificacoes:
                categoria_id = classificacoes[codigo]
                totais[categoria_id] += Decimal(str(resultado.valor))
                continue

            identificacao = (resultado.identificacao or "").lower()
            for categoria in categorias:
                termos = [t.lower() for t in (categoria.get("identificadores") or []) if t]
                if any(termo in identificacao for termo in termos):
                    totais[categoria["id"]] += Decimal(str(resultado.valor))
                    break

        for categoria in categorias:
            registro = upsert_despesa(
                rateio_id,
                mes,
                ano,
                categoria["id"],
                -totais[categoria["id"]],
            )
            registros.append(registro)

        if not gerar_cobranca or not pode_gerar_qrcode:
            continue

        total = -sum(totais.values())
        n_ativas = len(cotas)
        parcela = (
            (total / n_ativas).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if n_ativas
            else Decimal("0.00")
        )

        membros = listar_membros(rateio_id)
        valor_fixo_por_cota = {}
        for m in membros:
            if m.get("valor_fixo"):
                cid = m["cota_id"]
                valor_fixo_por_cota[cid] = valor_fixo_por_cota.get(cid, Decimal("0.00")) + Decimal(str(m["valor_fixo"]))

        financiadora_id = cota_financiadora(rateio_id, rateio.get("organizador_id"))

        for cota in cotas:
            identificador = cota["identificador"]

            # A cota financiadora (do organizador) adiantou as despesas; não recebe cobrança.
            if financiadora_id is not None and cota["id"] == financiadora_id:
                continue

            pendentes = cobrancas_status(
                mes=mes, ano=ano, status="enviado", cota=identificador
            )
            if len(pendentes) > 0:
                logging.info(
                    "Despesa já enviada para %s (%s/%s) no rateio %s.",
                    identificador,
                    mes,
                    ano,
                    rateio_id,
                )
                continue

            # O fundo entra na cobrança desta cota (valor padrão ou sobrescrito).
            fundo_extra = valor_fundo_da_cota(rateio, cota)
            # Abate apenas o valor fixo pago pelos membros da cota.
            valor_fixo = valor_fixo_por_cota.get(cota["id"], Decimal("0.00"))

            # QR = parcela + fundo - valor fixo.
            amount = max(
                (parcela - valor_fixo + fundo_extra).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
                Decimal("0.00"),
            )

            # Não gera QR Code quando não há valor a cobrar (coberto pelo valor fixo).
            if amount <= 0:
                logging.info(
                    "Cota %s sem valor a cobrar (%s/%s) no rateio %s.",
                    identificador,
                    mes,
                    ano,
                    rateio_id,
                )
                continue

            gerar_salvar_qrcode(
                mes=mes,
                ano=ano,
                cota=identificador,
                cota_id=cota["id"],
                identification=f'{identificador}{mes}{ano}',
                description=f'Conta{identificador}{mes}.{ano}',
                amount=amount,
                data_atual=normalizar_data_mysql(data_final),
            )

    return {"rateios": len(rateios), "registros": len(registros), "dados": registros}
