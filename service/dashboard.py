"""Monta os dados do painel financeiro dinâmico por rateio."""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from repository.categoria import listar_por_rateio as listar_categorias
from repository.cobranca import listar_por_cotas
from repository.cota import listar_por_rateio as listar_cotas
from repository.credito_cota import listar_por_rateio as listar_creditos
from repository.despesa import listar_por_rateio as listar_despesas
from repository.fechamento_cota import listar_por_rateio as listar_fechamentos
from repository.membro import listar_por_rateio as listar_membros
from repository.rateio import listar_por_membro, listar_por_organizador, listar_todos

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

        # Agrupa TODAS as cobranças (por membro) de cada cota/mês.
        cobrancas_map = {}
        for cb in listar_por_cotas([c["id"] for c in cotas]):
            cobrancas_map.setdefault((cb["mes"], cb["ano"], cb["cota_id"]), []).append(cb)

        nome_membro = {m["id"]: m["nome"] for m in listar_membros(rateio_id)}
        nome_cota = {c["id"]: c["identificador"] for c in cotas}

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
        total_pendente = Decimal("0.00")
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
                cobrancas = cobrancas_map.get((mes, ano, cota["id"]), [])

                # QRs da cota neste mês (um por membro, quando houver).
                qrs = []
                for cb in cobrancas:
                    rotulo = nome_membro.get(cb.get("membro_id")) or cota["identificador"]
                    qrs.append(
                        {
                            "valor": float(cb.get("valor") or 0),
                            "brcode": cb.get("brcode") or "",
                            "rotulo": rotulo,
                            "qr_url": (
                                f"https://br-se1.magaluobjects.com/qrcodepix/{cb['url_qrcode']}"
                                if cb.get("url_qrcode")
                                else None
                            ),
                        }
                    )

                # Transferências de saldo que afetam esta cota neste mês
                # (origem = saiu deste mês; destino = entrou neste mês).
                movimentacoes = []
                for cr in creditos:
                    if cr["cota_id"] != cota["id"]:
                        continue
                    if cr["origem_mes"] == mes and cr["origem_ano"] == ano:
                        movimentacoes.append(
                            {
                                "id": cr["id"],
                                "tipo": "origem",
                                "outro_mes": cr["destino_mes"],
                                "outro_ano": cr["destino_ano"],
                                "valor": float(cr["valor"]),
                            }
                        )
                    if cr["destino_mes"] == mes and cr["destino_ano"] == ano:
                        movimentacoes.append(
                            {
                                "id": cr["id"],
                                "tipo": "destino",
                                "outro_mes": cr["origem_mes"],
                                "outro_ano": cr["origem_ano"],
                                "valor": float(cr["valor"]),
                            }
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
                        "movimentacoes": movimentacoes,
                        "qrs": qrs,
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

            # Valor pendente = soma do que cada cota ainda não pagou (só o que falta).
            pendente_mes = Decimal("0.00")
            for cota in cotas:
                linha = next((c for c in cota_linhas if c["id"] == cota["id"]), None)
                pago = Decimal(str(linha["pagamentos_liquido"])) if linha else Decimal("0.00")
                pendente_mes += max(parcela - pago, Decimal("0.00"))
            total_pendente += pendente_mes

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

        valor_inicial_caixa = Decimal(str(rateio.get("valor_inicial_caixa") or 0))
        caixa_atual = (total_fundo_geral + valor_inicial_caixa).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        pendente = total_pendente.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        saldo = (caixa_atual - pendente).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        nome_por_cota = {c["id"]: c["identificador"] for c in cotas}
        transferencias = [
            {
                "id": cr["id"],
                "cota": nome_por_cota.get(cr["cota_id"], str(cr["cota_id"])),
                "origem_mes": cr["origem_mes"],
                "origem_ano": cr["origem_ano"],
                "destino_mes": cr["destino_mes"],
                "destino_ano": cr["destino_ano"],
                "valor": float(cr["valor"]),
            }
            for cr in creditos
        ]

        resultado.append(
            {
                "rateio": rateio,
                "cotas": cotas,
                "categorias": categorias,
                "meses": meses,
                "transferencias": transferencias,
                "totais": {
                    "total_despesas": float(total_despesas_geral),
                    "total_fundo": float(total_fundo_geral),
                    "caixa_atual": float(caixa_atual),
                    "total_pagamentos": float(total_pagamentos_geral),
                    "pendente": float(pendente),
                    "saldo": float(saldo),
                },
            }
        )

    return resultado
