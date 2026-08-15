"""Monta os dados do painel financeiro dinâmico por rateio."""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from repository.categoria import listar_por_rateio as listar_categorias
from repository.cobranca import listar_por_cotas
from repository.cota import listar_por_rateio as listar_cotas
from repository.credito_cota import listar_por_rateio as listar_creditos
from repository.despesa import listar_por_rateio as listar_despesas
from repository.fechamento_cota import listar_por_rateio as listar_fechamentos
from repository.rateio import listar_por_membro, listar_por_organizador, listar_todos
from service.rateio_service import valor_fundo_da_cota

MESES_ORDEM = {
    "Janeiro": 1,
    "Fevereiro": 2,
    "Março": 3,
    "Abril": 4,
    "Maio": 5,
    "Junho": 6,
    "Julho": 7,
    "Agosto": 8,
    "Setembro": 9,
    "Outubro": 10,
    "Novembro": 11,
    "Dezembro": 12,
}


def montar_dashboard(usuario=None):
    if usuario is None:
        rateios = listar_todos()
    elif usuario.get("perfil") == "organizador":
        rateios = listar_por_organizador(usuario["id"])
    else:
        rateios = listar_por_membro(usuario["id"])

    resultado = []
    for rateio in rateios:
        rateio_id = rateio["id"]
        cotas = [c for c in listar_cotas(rateio_id) if c.get("ativo")]
        categorias = listar_categorias(rateio_id)

        cobrancas_map = {
            (cb["mes"], cb["ano"], cb["cota_id"]): cb
            for cb in listar_por_cotas([c["id"] for c in cotas])
        }

        nome_categoria = {c["id"]: c["nome"] for c in categorias}

        fechamentos = listar_fechamentos(rateio_id)
        despesas_regs = listar_despesas(rateio_id)
        creditos = listar_creditos(rateio_id)

        fechamentos_map = {}
        for f in fechamentos:
            key = (f["mes"], f["ano"])
            fechamentos_map.setdefault(key, {})[f["cota_id"]] = {
                "pagamentos": f["pagamentos"],
                "fundo": f["fundo"],
                "saldo": f["saldo"],
            }

        creditos_movidos_map = {}
        creditos_recebidos_map = {}
        for cr in creditos:
            origem = (cr["cota_id"], cr["origem_mes"], cr["origem_ano"])
            destino = (cr["cota_id"], cr["destino_mes"], cr["destino_ano"])
            creditos_movidos_map[origem] = creditos_movidos_map.get(origem, Decimal("0.00")) + Decimal(str(cr["valor"]))
            creditos_recebidos_map[destino] = creditos_recebidos_map.get(destino, Decimal("0.00")) + Decimal(str(cr["valor"]))

        despesas_map = {}
        for d in despesas_regs:
            key = (d["mes"], d["ano"])
            despesas_map.setdefault(key, {})[d["categoria_id"]] = d["valor"]

        meses_keys = sorted(
            set(list(fechamentos_map.keys()) + list(despesas_map.keys())),
            key=lambda k: (k[1], MESES_ORDEM.get(k[0], 99)),
            reverse=True,
        )

        n_ativas = len(cotas)
        meses = []
        total_despesas_geral = Decimal("0.00")
        total_fundo_geral = Decimal("0.00")
        total_pagamentos_geral = Decimal("0.00")
        agora = datetime.now()

        for (mes, ano) in meses_keys:
            despesas_cat = despesas_map.get((mes, ano), {})
            total = sum(Decimal(str(v)) for v in despesas_cat.values())
            parcela = (
                (total / n_ativas).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if n_ativas
                else Decimal("0.00")
            )

            cota_linhas = []
            for cota in cotas:
                dados = fechamentos_map.get((mes, ano), {}).get(cota["id"], {})
                enviado = creditos_movidos_map.get((cota["id"], mes, ano), Decimal("0.00"))
                recebido = creditos_recebidos_map.get((cota["id"], mes, ano), Decimal("0.00"))
                pagamentos_bruto = Decimal(str(dados.get("pagamentos", 0)))
                cobranca = cobrancas_map.get((mes, ano, cota["id"]))
                qr_url = (
                    f"https://br-se1.magaluobjects.com/qrcodepix/{cobranca['url_qrcode']}"
                    if cobranca and cobranca.get("url_qrcode")
                    else None
                )
                cota_linhas.append(
                    {
                        "id": cota["id"],
                        "identificador": cota["identificador"],
                        "pagamentos": dados.get("pagamentos", 0),
                        "pagamentos_liquido": float(pagamentos_bruto - enviado),
                        "fundo": dados.get("fundo", 0),
                        "saldo": dados.get("saldo", 0),
                        "transferido": float(recebido - enviado),
                        "qr_url": qr_url,
                        "cobranca_notificada": cobranca.get("notificacao_whatsapp") if cobranca else None,
                    }
                )

            total_despesas_geral += total
            total_fundo_mes = sum(Decimal(str(c["fundo"])) for c in cota_linhas)
            total_pagamentos_mes = sum(Decimal(str(c["pagamentos"])) for c in cota_linhas)
            total_pagamentos_liquido_mes = sum(
                Decimal(str(c["pagamentos_liquido"])) for c in cota_linhas
            )
            total_fundo_geral += total_fundo_mes
            total_pagamentos_geral += total_pagamentos_mes

            # Valor pendente = soma do que cada cota ainda deve (parcela + fundo).
            pendente_mes = Decimal("0.00")
            for cota in cotas:
                linha = next((c for c in cota_linhas if c["id"] == cota["id"]), None)
                pago = Decimal(str(linha["pagamentos_liquido"])) if linha else Decimal("0.00")
                fundo_esperado = valor_fundo_da_cota(rateio, cota)
                pendente_mes += max(parcela + fundo_esperado - pago, Decimal("0.00"))

            if ano == agora.year and MESES_ORDEM.get(mes, 0) == agora.month:
                status = "em andamento"
            elif pendente_mes <= Decimal("0.01"):
                status = "correto"
            else:
                status = "atraso"

            meses.append(
                {
                    "mes": mes,
                    "ano": ano,
                    "despesas": {nome_categoria.get(cat_id, cat_id): valor for cat_id, valor in despesas_cat.items()},
                    "total": float(total),
                    "parcela": float(parcela),
                    "total_fundo": float(total_fundo_mes),
                    "total_pagamentos": float(total_pagamentos_mes),
                    "total_pagamentos_liquido": float(total_pagamentos_liquido_mes),
                    "status": status,
                    "cotas": cota_linhas,
                }
            )

        pendente = total_despesas_geral - (total_pagamentos_geral - total_fundo_geral)
        saldo = total_fundo_geral - pendente

        resultado.append(
            {
                "rateio": rateio,
                "cotas": cotas,
                "categorias": categorias,
                "meses": meses,
                "totais": {
                    "total_despesas": float(total_despesas_geral),
                    "total_fundo": float(total_fundo_geral),
                    "total_pagamentos": float(total_pagamentos_geral),
                    "pendente": float(pendente),
                    "saldo": float(saldo),
                },
            }
        )

    return resultado
