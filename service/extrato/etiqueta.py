"""Etiqueta de reconhecimento dos lançamentos do extrato (somente leitura).

Usada na tela /extrato para mostrar se cada lançamento já é reconhecido por um
identificador salvo (categoria p/ débito, membro p/ crédito), por uma regra
manual de classificação (classificacao_manual), ou se ainda está sem etiqueta.
Espelha as regras de casamento usadas em fechar_despesas / fechar_pagamentos.
"""
from dto.fechamento_requests import get_transacao_debito


def _primeiro_termo_casado(termos, identificacao):
    """Retorna o primeiro termo (original) cujo texto, em minúsculas, esteja
    contido na identificação, ou None."""
    texto = (identificacao or "").lower()
    for termo in termos or []:
        if termo and str(termo).lower() in texto:
            return termo
    return None


def montar_etiqueta(transacao, categorias, map_classificacao, membros, nome_cota=None):
    """Calcula a etiqueta de um lançamento do extrato.

    transacao: dict com pelo menos banco, tipo_transacao, identificacao e
    codigo_transacao.
    categorias: lista de categorias ativas com id, nome e identificadores.
    map_classificacao: dict codigo_transacao -> categoria_id (classificacao_manual).
    membros: lista de membros ativos com id, nome, cota_id e
    identificadores_pagamento.
    nome_cota: opcional, dict cota_id -> identificador (ex.: 2 -> "AP2").

    Retorna dict com etiqueta_tipo, etiqueta_texto, etiqueta_classe,
    etiqueta_identificador (e categoria_id/membro_id/cota_id quando aplicável).
    """
    eh_debito = transacao.get("tipo_transacao") == get_transacao_debito(transacao.get("banco"))
    identificacao = transacao.get("identificacao", "")

    if eh_debito:
        # 1) Regra manual salva (classificacao_manual) tem prioridade.
        categoria_id = map_classificacao.get(transacao.get("codigo_transacao"))
        if categoria_id:
            nome = next(
                (c["nome"] for c in categorias if c["id"] == categoria_id),
                f"categoria {categoria_id}",
            )
            return {
                "etiqueta_tipo": "regra_salva",
                "etiqueta_texto": nome,
                "etiqueta_classe": "bg-primary",
                "etiqueta_identificador": "",
                "categoria_id": categoria_id,
            }

        # 2) Match por identificadores das categorias.
        for categoria in categorias:
            termo = _primeiro_termo_casado(categoria.get("identificadores"), identificacao)
            if termo:
                return {
                    "etiqueta_tipo": "identificado",
                    "etiqueta_texto": categoria["nome"],
                    "etiqueta_classe": "bg-success",
                    "etiqueta_identificador": termo,
                    "categoria_id": categoria["id"],
                }
    else:
        # Crédito: match por identificadores de pagamento dos membros.
        for membro in membros:
            termo = _primeiro_termo_casado(membro.get("identificadores_pagamento"), identificacao)
            if termo:
                cota = ""
                if nome_cota and membro.get("cota_id") is not None:
                    cota = nome_cota.get(membro["cota_id"], "")
                prefixo = f"{cota} · " if cota else ""
                return {
                    "etiqueta_tipo": "identificado",
                    "etiqueta_texto": f'{prefixo}{membro["nome"]}',
                    "etiqueta_classe": "bg-success",
                    "etiqueta_identificador": termo,
                    "membro_id": membro["id"],
                    "cota_id": membro.get("cota_id"),
                }

    return {
        "etiqueta_tipo": "sem_etiqueta",
        "etiqueta_texto": "",
        "etiqueta_classe": "",
        "etiqueta_identificador": "",
    }
