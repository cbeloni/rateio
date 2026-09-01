"""Regras de negócio compartilhadas do modelo de rateio."""


def cota_financiadora(rateio_id: int, organizador_id: int):
    """Cota do organizador (financiadora).

    O financiador é sempre quem criou o rateio: a cota que possui um membro
    vinculado ao usuário organizador. Retorna o id da cota ou None.
    """
    from repository.cota import listar_por_rateio
    from repository.membro import listar_por_cota

    if not organizador_id:
        return None

    for cota in listar_por_rateio(rateio_id, apenas_ativas=True):
        for membro in listar_por_cota(cota["id"]):
            if membro.get("usuario_id") == organizador_id:
                return cota["id"]
    return None
