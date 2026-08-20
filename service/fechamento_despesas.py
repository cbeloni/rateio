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
from repository.responsabilidade import listar_por_rateio as listar_responsabilidades
from service.drive_service import get_last_file_from_drive
from service.qrcode_service import gerar_salvar_qrcode
from service.rateio_service import cota_financiadora
from util.datas_uteis import meses_portugues, normalizar_data_mysql, ultimo_dia_mes_atual


def _valor_fixo_por_cota(categorias):
    """Soma dos valores fixos por cota (categorias com valor_fixo preenchido)."""
    total = Decimal("0.00")
    for c in categorias:
        if c.get("valor_fixo") is not None:
            total += Decimal(str(c["valor_fixo"]))
    return total


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
        # Os valores das despesas são atualizados todos os dias (cron diária), mas
        # o QRcode só é gerado no dia do fechamento A PARTIR DAS 23h, para que a
        # cobrança saia na virada do mês (último dia às 23h).
        pode_gerar_qrcode = not valida_mes or (
            datetime.now().day == dia_do_fechamento and datetime.now().hour >= 23
        )

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

        n_ativas = len(cotas)
        caixa_por_cota = _valor_fixo_por_cota(categorias)

        # Categorias fixas (valor_fixo por cota) são obrigação mensal, não vêm do extrato.
        for categoria in categorias:
            valor = -totais[categoria["id"]]
            if categoria.get("valor_fixo") is not None:
                valor += Decimal(str(categoria["valor_fixo"])) * n_ativas
            registro = upsert_despesa(rateio_id, mes, ano, categoria["id"], valor)
            registros.append(registro)

        if not gerar_cobranca or not pode_gerar_qrcode:
            continue

        total = -sum(totais.values()) + (caixa_por_cota * n_ativas)
        parcela = (
            (total / n_ativas).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if n_ativas
            else Decimal("0.00")
        )

        membros = listar_membros(rateio_id)
        responsabilidades = listar_responsabilidades(rateio_id)

        resp_por_membro = {}
        for r in responsabilidades:
            resp_por_membro.setdefault(r["membro_id"], []).append(r["categoria_id"])

        categorias_por_id = {c["id"]: c for c in categorias}

        financiadora_id = cota_financiadora(rateio_id, rateio.get("organizador_id"))

        for cota in cotas:
            identificador = cota["identificador"]

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

            membros_da_cota = [m for m in membros if m["cota_id"] == cota["id"]]
            principal = next((m for m in membros_da_cota if m.get("principal")), None)
            if principal is None and membros_da_cota:
                principal = membros_da_cota[0]

            atribuido = Decimal("0.00")
            for membro in membros_da_cota:
                for categoria_id in resp_por_membro.get(membro["id"], []):
                    categoria = categorias_por_id.get(categoria_id)
                    if not categoria:
                        continue
                    if categoria.get("valor_fixo") is not None:
                        valor = Decimal(str(categoria["valor_fixo"]))
                    else:
                        # Categoria do extrato: parcela da categoria na cota.
                        valor = (
                            (Decimal(str(-totais.get(categoria_id, Decimal("0.00")))) / n_ativas)
                            .quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        )
                    if valor <= 0:
                        continue
                    atribuido += valor
                    gerar_salvar_qrcode(
                        mes=mes,
                        ano=ano,
                        cota=identificador,
                        cota_id=cota["id"],
                        membro_id=membro["id"],
                        identification=f'M{membro["id"]}C{categoria_id}{mes}{ano}',
                        description=f'Conta{identificador}{mes}{ano}',
                        amount=valor,
                        data_atual=normalizar_data_mysql(data_final),
                    )

            restante = (parcela - atribuido).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if restante > 0 and principal:
                gerar_salvar_qrcode(
                    mes=mes,
                    ano=ano,
                    cota=identificador,
                    cota_id=cota["id"],
                    membro_id=principal["id"],
                    identification=f'M{principal["id"]}P{mes}{ano}',
                    description=f'Conta{identificador}{mes}{ano}',
                    amount=restante,
                    data_atual=normalizar_data_mysql(data_final),
                )

    return {"rateios": len(rateios), "registros": len(registros), "dados": registros}
