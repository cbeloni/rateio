"""Seed do rateio (condomínio padrão AP1–AP4) no novo modelo genérico.

Execução (a partir da raiz do projeto):
    python scripts/seed_rateio_condominio.py [--rateio-id 1]

Popula o rateio indicado com cotas AP1–AP4, membros e categorias.

Formato dos nomes: cada nome vira um membro. Quando um nome está entre parênteses,
o identificador da esquerda é vinculado ao membro da direita. Ex.:
    "meuoculos.com(everton silva)" -> o identificador "meuoculos.com" pertence ao
    membro "everton silva".
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.database import get_session
from repository.categoria import Categoria, buscar_por_nome as buscar_categoria_por_nome
from repository.cota import Cota
from repository.membro import Membro
from repository.rateio import buscar_por_id as buscar_rateio

# Dados que antes ficavam fixos no código (util/identificadores.py).
APARTAMENTOS = {
    "AP1": {
        "nomes": ["everton silva", "alexandre tomassine", "alexandre toma(alexandre tomassine)", "meuoculos.com(everton silva)"],
        "email": "everton.silvasousa@gmail.com",
        "telefone": "5511998107488",
    },
    "AP2": {
        "nomes": ["ana carolina"],
        "email": "anacarolina.bnl@gmail.com",
        "telefone": "5512988591266",
    },
    "AP3": {
        "nomes": ["tathiane de almeida", "filipe", "tathy modas(tathiane de almeida)"],
        "email": "tathigarcia@hotmail.com",
        "telefone": "5511983012408",
    },
    "AP4": {
        "nomes": ["cauê beloni", "caue beloni(cauê beloni)", "raquel santos"],
        "email": "caue.beloni@unifesp.br",
        "telefone": "5511986768497",
    },
}

CATEGORIAS = [
    ("enel", ["enel"], 1),
    ("sabesp", ["sabesp", "cia de saneamento basico", "saneamento"], 2),
    ("faxina", ["edileuza"], 3),
    ("outros", ["ecoville", "assai atacadista", "sonda", "carrefour", "shpp"], 4),
]


def _parse_membros(nomes):
    """Converte a lista de nomes em membros, vinculando identificadores entre parênteses."""
    membros = {}
    for entrada in nomes:
        entrada = entrada.strip()
        if "(" in entrada:
            identificador = entrada.split("(")[0].strip()
            membro_pai = entrada.split("(")[1].rstrip(")").strip()
            membros.setdefault(membro_pai, {"nome": membro_pai, "identificadores": []})
            membros[membro_pai]["identificadores"].append(identificador)
        else:
            membros.setdefault(entrada, {"nome": entrada, "identificadores": []})

    return [
        {"nome": d["nome"], "identificadores": [d["nome"]] + d["identificadores"]}
        for d in membros.values()
    ]


def _buscar_cota_por_identificador(rateio_id, identificador):
    """Busca cota por identificador sem diferenciar maiúsculas/minúsculas."""
    session = get_session()
    cotas = session.query(Cota).filter(Cota.rateio_id == rateio_id).all()
    session.close()
    alvo = identificador.lower()
    for cota in cotas:
        if (cota.identificador or "").lower() == alvo:
            return cota
    return None


def main():
    parser = argparse.ArgumentParser(description="Seed do condomínio padrão.")
    parser.add_argument("--rateio-id", type=int, default=1, help="ID do rateio a popular (default: 1)")
    args = parser.parse_args()

    rateio = buscar_rateio(args.rateio_id)
    if not rateio:
        print(f"Rateio {args.rateio_id} não encontrado.")
        sys.exit(1)
    print(f"Rateio: id={rateio.id} nome={rateio.nome}")

    for nome, identificadores, ordem in CATEGORIAS:
        categoria = buscar_categoria_por_nome(rateio.id, nome)
        if not categoria:
            categoria = Categoria(
                rateio_id=rateio.id,
                nome=nome,
                identificadores=identificadores,
                ordem=ordem,
                ativo=True,
            )
            categoria.save()
        print(f"Categoria {nome} criada/recuperada.")

    for ordem, (identificador, dados) in enumerate(APARTAMENTOS.items(), start=1):
        cota = _buscar_cota_por_identificador(rateio.id, identificador)
        if not cota:
            cota = Cota(
                rateio_id=rateio.id,
                identificador=identificador,
                ordem=ordem,
                ativo=True,
            )
            cota.save()
            cota = _buscar_cota_por_identificador(rateio.id, identificador)
        elif cota.identificador != identificador or cota.ordem != ordem:
            # Normaliza identificador e ordem da cota existente.
            session = get_session()
            cota.identificador = identificador
            cota.ordem = ordem
            session.merge(cota)
            session.commit()
            session.close()
        print(f"Cota {identificador} id={cota.id}")

        membros = _parse_membros(dados["nomes"])
        session = get_session()
        for i, membro_dados in enumerate(membros):
            existe = (
                session.query(Membro)
                .filter(Membro.cota_id == cota.id, Membro.nome == membro_dados["nome"])
                .first()
                is not None
            )
            if not existe:
                session.add(
                    Membro(
                        cota_id=cota.id,
                        nome=membro_dados["nome"],
                        email=dados["email"] if i == 0 else None,
                        telefone=dados["telefone"] if i == 0 else None,
                        identificadores_pagamento=membro_dados["identificadores"],
                        ativo=True,
                    )
                )
        session.commit()
        session.close()
        print(f"  Membros: {[m['nome'] for m in membros]}")

    print("Seed concluído.")


if __name__ == "__main__":
    main()
