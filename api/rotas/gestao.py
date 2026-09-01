"""Rotas de gestão de rateios (páginas HTML)."""
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request

from config.database import get_session
from dto.cobrar_request import CobrarRequest
from dto.fechamento_requests import get_transacao_debito
from repository.categoria import (
    Categoria,
    buscar_por_id as buscar_categoria,
    listar_por_rateio as listar_categorias,
)
from repository.classificacao_manual import (
    listar_por_rateio as listar_classificacao,
    salvar as salvar_classificacao_manual,
)
from repository.cota import (
    Cota,
    buscar_por_id as buscar_cota,
    listar_por_rateio as listar_cotas,
)
from repository.membro import (
    Membro,
    buscar_por_id as buscar_membro,
    listar_por_cota as listar_membros,
    listar_por_rateio as listar_membros_rateio,
)
from repository.fechamento_cota import FechamentoCota
from repository.extrato import ExtratoRepository, listar_por_rateio as listar_extrato
from repository.rateio import (
    Rateio,
    buscar_por_id as buscar_rateio,
    desativar as desativar_rateio_db,
    listar_por_membro,
    listar_por_organizador,
)
from repository.usuario import PERFIS, Usuario, buscar_por_email, listar_usuarios
from repository.credito_cota import buscar_por_id as buscar_credito
from repository.credito_cota import mover as mover_credito, remover as remover_credito
from repository.responsabilidade import listar_por_rateio as listar_responsabilidades, substituir_do_membro
from service.auth_service import exigir_login, hash_senha
from service.cobrar_service import cobrar_cota as cobrar_cota_service, cobrar_e_enviar_whatsapp
from service.dashboard import montar_dashboard
from service.extrato.etiqueta import montar_etiqueta
from service.fechamento_despesas import fechar_despesas
from service.fechamento_pagamento import fechar_pagamentos, recalcular_fechamentos

from ..dependencias import templates

router = APIRouter()


def _decimal_ou(valor, default=None):
    texto = str(valor).strip().replace(",", ".") if valor is not None else ""
    if not texto:
        return default
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return default


def _parse_identificadores(texto):
    return [s.strip() for s in (texto or "").split(",") if s.strip()]


def _perfil_membro(valor, padrao="membro"):
    perfil = str(valor or "").strip().lower()
    return perfil if perfil in PERFIS else padrao


MESES_NUMERO = {
    "Janeiro": 1, "Fevereiro": 2, "Março": 3, "Abril": 4, "Maio": 5, "Junho": 6,
    "Julho": 7, "Agosto": 8, "Setembro": 9, "Outubro": 10, "Novembro": 11, "Dezembro": 12,
}
MESES_NOME = {v: k for k, v in MESES_NUMERO.items()}


def _proximo_mes_ano(mes, ano):
    numero = MESES_NUMERO.get(mes, 1)
    if numero == 12:
        return "Janeiro", ano + 1
    return MESES_NOME[numero + 1], ano


def _ultimo_dia(mes_numero, ano):
    import calendar

    return f"{calendar.monthrange(ano, mes_numero)[1]:02d}/{mes_numero:02d}/{ano}"


def _decimo_dia_proximo_mes(mes_numero, ano):
    """Dia 10 do mês seguinte (janela para capturar pagamentos atrasados)."""
    if mes_numero == 12:
        return f"10/01/{ano + 1}"
    return f"10/{mes_numero + 1:02d}/{ano}"


def _periodo_pagamentos(mes_numero, ano):
    """Pagamentos do mês M são feitos no mês seguinte (M+1).

    Retorna (data_inicial, data_final, nome_do_mes) do período de pagamentos.
    """
    if mes_numero == 12:
        mes_seguinte = 1
        ano_seguinte = ano + 1
    else:
        mes_seguinte = mes_numero + 1
        ano_seguinte = ano
    data_inicial = f"01/{mes_seguinte:02d}/{ano_seguinte}"
    data_final = _ultimo_dia(mes_seguinte, ano_seguinte)
    mes_nome = MESES_NOME.get(mes_numero, mes_numero)
    return data_inicial, data_final, mes_nome


def _mes_mais_antigo(mes1, ano1, mes2, ano2):
    """Retorna a tupla (mes, ano) cronologicamente menor entre os dois períodos."""
    ordem1 = (ano1, MESES_NUMERO.get(mes1, 99))
    ordem2 = (ano2, MESES_NUMERO.get(mes2, 99))
    return (mes1, ano1) if ordem1 <= ordem2 else (mes2, ano2)


def _membro_de_rateio(usuario_id: int, rateio_id: int) -> bool:
    """Verifica se o usuário é membro de alguma cota do rateio."""
    for cota in listar_cotas(rateio_id):
        for membro in listar_membros(cota["id"]):
            if membro.get("usuario_id") == usuario_id and membro.get("ativo"):
                return True
    return False


def _rateios_visiveis(usuario):
    """Rateios próprios e rateios nos quais o usuário é membro."""
    rateios = listar_por_organizador(usuario["id"]) + listar_por_membro(usuario["id"])
    return list({rateio["id"]: rateio for rateio in rateios}.values())


def _rateio_acessivel(usuario, rateio_id):
    rateio = buscar_rateio(rateio_id)
    if not rateio:
        return None
    if rateio.organizador_id == usuario["id"]:
        return rateio
    if _membro_de_rateio(usuario["id"], rateio_id):
        return rateio
    return None


def _rateio_do_organizador(usuario, rateio_id):
    """Rateio acessível apenas para escrita (organizador dono)."""
    rateio = buscar_rateio(rateio_id)
    if not rateio:
        return None
    if rateio.organizador_id == usuario["id"]:
        return rateio
    return None


@router.get("/rateios", response_class=HTMLResponse)
async def pagina_rateios(request: Request):
    usuario = exigir_login(request)
    rateios = _rateios_visiveis(usuario)
    return templates.TemplateResponse(
        "rateios.html",
        {"request": request, "usuario": usuario, "rateios": rateios},
    )


@router.post("/rateios", response_class=HTMLResponse)
async def criar_rateio(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    nome = str(form.get("nome", "")).strip()
    descricao = str(form.get("descricao", "")).strip() or None
    valor_fundo_padrao = _decimal_ou(form.get("valor_fundo_padrao"), Decimal("0.00"))
    valor_inicial_caixa = _decimal_ou(form.get("valor_inicial_caixa"), Decimal("0.00"))
    pluggy_client_id = str(form.get("pluggy_client_id", "")).strip() or None
    pluggy_client_secret = str(form.get("pluggy_client_secret", "")).strip() or None
    pluggy_account_id = str(form.get("pluggy_account_id", "")).strip() or None
    dia_fechamento_raw = str(form.get("dia_fechamento", "")).strip()
    dia_fechamento = int(dia_fechamento_raw) if dia_fechamento_raw.isdigit() else 0

    if not nome:
        return RedirectResponse(url="/rateios?erro=Nome+obrigatorio", status_code=303)

    rateio = Rateio(
        nome=nome,
        organizador_id=usuario["id"],
        descricao=descricao,
        valor_fundo_padrao=valor_fundo_padrao,
        valor_inicial_caixa=valor_inicial_caixa,
        dia_fechamento=dia_fechamento,
        pluggy_client_id=pluggy_client_id,
        pluggy_client_secret=pluggy_client_secret,
        pluggy_account_id=pluggy_account_id,
    )
    rateio.save()
    return RedirectResponse(url=f"/rateios/{rateio.id}?mensagem=Rateio+criado+com+sucesso", status_code=303)


@router.post("/rateios/{rateio_id}/remover", response_class=HTMLResponse)
async def remover_rateio(request: Request, rateio_id: int):
    usuario = exigir_login(request)
    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio:
        return RedirectResponse(url="/rateios", status_code=303)

    desativar_rateio_db(rateio_id)
    return RedirectResponse(url="/rateios?mensagem=Rateio+desativado", status_code=303)


@router.post("/rateios/{rateio_id}", response_class=HTMLResponse)
async def salvar_rateio(request: Request, rateio_id: int):
    usuario = exigir_login(request)
    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio:
        return RedirectResponse(url="/rateios", status_code=303)

    form = await request.form()
    rateio.nome = str(form.get("nome", "")).strip() or rateio.nome
    rateio.descricao = str(form.get("descricao", "")).strip() or None
    rateio.valor_fundo_padrao = _decimal_ou(
        form.get("valor_fundo_padrao"), rateio.valor_fundo_padrao
    )
    rateio.valor_inicial_caixa = _decimal_ou(
        form.get("valor_inicial_caixa"), rateio.valor_inicial_caixa
    )
    rateio.pluggy_client_id = str(form.get("pluggy_client_id", "")).strip() or None
    rateio.pluggy_client_secret = str(form.get("pluggy_client_secret", "")).strip() or None
    rateio.pluggy_account_id = str(form.get("pluggy_account_id", "")).strip() or None
    dia_fechamento_raw = str(form.get("dia_fechamento", "")).strip()
    rateio.dia_fechamento = int(dia_fechamento_raw) if dia_fechamento_raw.isdigit() else rateio.dia_fechamento

    session = get_session()
    session.merge(rateio)
    session.commit()
    session.close()

    return RedirectResponse(url=f"/rateios/{rateio_id}?mensagem=Configuracao+salva+com+sucesso", status_code=303)


@router.get("/rateios/{rateio_id}", response_class=HTMLResponse)
async def pagina_rateio(request: Request, rateio_id: int):
    usuario = exigir_login(request)
    rateio = _rateio_acessivel(usuario, rateio_id)
    if not rateio:
        return RedirectResponse(url="/rateios", status_code=303)

    cotas = listar_cotas(rateio_id)
    for cota in cotas:
        cota["membros"] = listar_membros(cota["id"])

    categorias = listar_categorias(rateio_id)

    return templates.TemplateResponse(
        "rateio.html",
        {
            "request": request,
            "usuario": usuario,
            "rateio": rateio.to_dict(),
            "cotas": cotas,
            "categorias": categorias,
        },
    )


@router.post("/cotas", response_class=HTMLResponse)
async def criar_cota(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)
    identificador = str(form.get("identificador", "")).strip()
    descricao = str(form.get("descricao", "")).strip() or None
    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio or not identificador:
        return RedirectResponse(url=f"/rateios/{rateio_id}", status_code=303)

    cota = Cota(
        rateio_id=rateio_id,
        identificador=identificador,
        descricao=descricao,
        ordem=len(listar_cotas(rateio_id)) + 1,
        ativo=True,
    )
    cota.save()
    return RedirectResponse(url=f"/cotas/{cota.id}?mensagem=Cota+criada+com+sucesso", status_code=303)


@router.get("/cotas/{cota_id}", response_class=HTMLResponse)
async def pagina_cota(request: Request, cota_id: int):
    usuario = exigir_login(request)
    cota = buscar_cota(cota_id)
    if not cota:
        return RedirectResponse(url="/rateios", status_code=303)

    rateio = _rateio_acessivel(usuario, cota.rateio_id)
    if not rateio:
        return RedirectResponse(url="/rateios", status_code=303)

    membros = listar_membros(cota_id)
    cotas = listar_cotas(cota.rateio_id)
    usuarios = listar_usuarios()
    categorias = listar_categorias(cota.rateio_id)

    resp_por_membro = {}
    for r in listar_responsabilidades(cota.rateio_id):
        resp_por_membro.setdefault(r["membro_id"], set()).add(r["categoria_id"])
    nomes_categoria = {c["id"]: c["nome"] for c in categorias}
    for m in membros:
        ids = sorted(resp_por_membro.get(m["id"], set()))
        m["categorias_responsavel"] = ids
        m["categorias_responsavel_nomes"] = [nomes_categoria.get(cid, str(cid)) for cid in ids]

    return templates.TemplateResponse(
        "cota.html",
        {
            "request": request,
            "usuario": usuario,
            "rateio": rateio.to_dict(),
            "cota": cota.to_dict(),
            "membros": membros,
            "cotas": cotas,
            "usuarios": usuarios,
            "categorias": categorias,
        },
    )


@router.post("/cotas/{cota_id}", response_class=HTMLResponse)
async def salvar_cota(request: Request, cota_id: int):
    usuario = exigir_login(request)
    cota = buscar_cota(cota_id)
    if not cota:
        return RedirectResponse(url="/rateios", status_code=303)

    rateio = _rateio_do_organizador(usuario, cota.rateio_id)
    if not rateio:
        return RedirectResponse(url="/rateios", status_code=303)

    form = await request.form()
    cota.identificador = str(form.get("identificador", "")).strip() or cota.identificador
    cota.descricao = str(form.get("descricao", "")).strip() or None

    cota.ativo = form.get("ativo") is not None

    session = get_session()
    session.merge(cota)
    session.commit()
    session.close()

    return RedirectResponse(url=f"/cotas/{cota_id}?mensagem=Cota+salva+com+sucesso", status_code=303)


@router.post("/membros", response_class=HTMLResponse)
async def criar_membro(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    cota_id = int(form.get("cota_id", "0") or 0)
    nome = str(form.get("nome", "")).strip()
    email = str(form.get("email", "")).strip() or None
    telefone = str(form.get("telefone", "")).strip() or None
    identificadores = _parse_identificadores(form.get("identificadores", ""))
    senha_inicial = str(form.get("senha_inicial", "")).strip() or None
    principal = form.get("principal") is not None
    receber_mensagens = form.get("receber_mensagens") is not None
    perfil = (
        "organizador"
        if email and email.casefold() == usuario["email"].casefold()
        else "membro"
    )

    cota = buscar_cota(cota_id)
    if not cota or not nome:
        return RedirectResponse(url="/rateios", status_code=303)

    rateio = _rateio_do_organizador(usuario, cota.rateio_id)
    if not rateio:
        return RedirectResponse(url="/rateios", status_code=303)

    categoria_ids = form.getlist("categorias_responsavel")
    membro_salvo = _salvar_membro(
        cota_id,
        nome,
        email,
        telefone,
        identificadores,
        senha_inicial=senha_inicial,
        perfil=perfil,
        principal=principal,
        receber_mensagens=receber_mensagens,
    )
    if membro_salvo:
        substituir_do_membro(cota.rateio_id, membro_salvo["id"], categoria_ids)
    return RedirectResponse(url=f"/cotas/{cota_id}?mensagem=Membro+adicionado+com+sucesso", status_code=303)


@router.post("/membros/{membro_id}", response_class=HTMLResponse)
async def salvar_membro(request: Request, membro_id: int):
    usuario = exigir_login(request)
    form = await request.form()

    session = get_session()
    membro = session.query(Membro).filter(Membro.id == membro_id).first()
    if not membro:
        session.close()
        return RedirectResponse(url="/rateios", status_code=303)
    cota_id = membro.cota_id
    session.close()

    cota = buscar_cota(cota_id)
    if not cota:
        return RedirectResponse(url="/rateios", status_code=303)
    rateio = _rateio_do_organizador(usuario, cota.rateio_id)
    if not rateio:
        return RedirectResponse(url="/rateios", status_code=303)

    nome = str(form.get("nome", "")).strip()
    email = str(form.get("email", "")).strip() or None
    telefone = str(form.get("telefone", "")).strip() or None
    identificadores = _parse_identificadores(form.get("identificadores", ""))
    principal = form.get("principal") is not None
    receber_mensagens = form.get("receber_mensagens") is not None
    perfil = _perfil_membro(form.get("perfil"))

    categoria_ids = form.getlist("categorias_responsavel")
    _salvar_membro(
        cota_id,
        nome,
        email,
        telefone,
        identificadores,
        membro_id=membro_id,
        perfil=perfil,
        principal=principal,
        receber_mensagens=receber_mensagens,
    )
    substituir_do_membro(cota.rateio_id, membro_id, categoria_ids)
    return RedirectResponse(url=f"/cotas/{cota_id}?mensagem=Membro+salvo+com+sucesso", status_code=303)


def _vincular_usuario(nome, email, senha_inicial):
    """Cria (ou reutiliza) a conta de usuário do membro. Retorna usuario_id ou None."""
    if not email or not senha_inicial:
        return None

    existente = buscar_por_email(email)
    if existente:
        return existente.id

    senha_hash, salt = hash_senha(senha_inicial)
    usuario = Usuario(
        nome=nome,
        email=email,
        senha_hash=f"{salt}:{senha_hash}",
        perfil="membro",
        ativo=True,
    )
    usuario.save()
    return usuario.id


def _salvar_membro(cota_id, nome, email, telefone, identificadores, usuario_id=None, membro_id=None, senha_inicial=None, perfil="membro", principal=False, receber_mensagens=True):
    if senha_inicial and email:
        usuario_id = _vincular_usuario(nome, email, senha_inicial)
    elif email and usuario_id is None:
        existente = buscar_por_email(email)
        if existente:
            usuario_id = existente.id

    session = get_session()
    if membro_id:
        membro = session.query(Membro).filter(Membro.id == membro_id).first()
        if not membro:
            session.close()
            return None
        membro.nome = nome
        membro.perfil = _perfil_membro(perfil)
        membro.email = email
        membro.telefone = telefone
        membro.principal = bool(principal)
        membro.receber_mensagens = bool(receber_mensagens)
        membro.identificadores_pagamento = identificadores
        membro.usuario_id = usuario_id
    else:
        membro = Membro(
            cota_id=cota_id,
            nome=nome,
            perfil=_perfil_membro(perfil),
            email=email,
            telefone=telefone,
            principal=bool(principal),
            receber_mensagens=bool(receber_mensagens),
            identificadores_pagamento=identificadores,
            usuario_id=usuario_id,
            ativo=True,
        )
        session.add(membro)

    session.commit()
    if principal:
        # Garante um único membro principal por cota.
        session.query(Membro).filter(
            Membro.cota_id == cota_id,
            Membro.id != membro.id,
        ).update({Membro.principal: False})
        session.commit()

    # Recarrega o membro após os commits e extrai o dicionário ANTES de fechar a
    # sessão, evitando DetachedInstanceError ao acessar atributos expirados.
    session.refresh(membro)
    resultado = membro.to_dict()
    session.close()
    return resultado


@router.get("/categorias", response_class=HTMLResponse)
async def pagina_categorias(request: Request):
    usuario = exigir_login(request)
    rateios = _rateios_visiveis(usuario)

    rateio_id = int(request.query_params.get("rateio_id", "0") or 0)
    if not rateio_id and rateios:
        rateio_id = rateios[0]["id"]

    rateio = _rateio_acessivel(usuario, rateio_id) if rateio_id else None
    categorias = listar_categorias(rateio_id) if rateio else []

    return templates.TemplateResponse(
        "categorias.html",
        {
            "request": request,
            "usuario": usuario,
            "rateios": rateios,
            "rateio": rateio.to_dict() if rateio else None,
            "categorias": categorias,
        },
    )


@router.post("/categorias", response_class=HTMLResponse)
async def criar_categoria(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)
    nome = str(form.get("nome", "")).strip()
    cor = str(form.get("cor", "")).strip() or None
    ordem_raw = str(form.get("ordem", "")).strip()
    ordem = int(ordem_raw) if ordem_raw else 0
    identificadores = _parse_identificadores(form.get("identificadores", ""))

    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio or not nome:
        return RedirectResponse(url=f"/categorias?rateio_id={rateio_id}", status_code=303)

    valor_fixo = _decimal_ou(form.get("valor_fixo"), None)
    categoria = Categoria(
        rateio_id=rateio_id,
        nome=nome,
        identificadores=identificadores,
        valor_fixo=valor_fixo,
        cor=cor,
        ordem=ordem,
        ativo=True,
    )
    categoria.save()
    return RedirectResponse(url=f"/categorias?rateio_id={rateio_id}&mensagem=Categoria+criada+com+sucesso", status_code=303)


@router.post("/categorias/{categoria_id}", response_class=HTMLResponse)
async def salvar_categoria(request: Request, categoria_id: int):
    usuario = exigir_login(request)
    categoria = buscar_categoria(categoria_id)
    if not categoria:
        return RedirectResponse(url="/categorias", status_code=303)

    rateio = _rateio_do_organizador(usuario, categoria.rateio_id)
    if not rateio:
        return RedirectResponse(url="/categorias", status_code=303)

    form = await request.form()
    categoria.nome = str(form.get("nome", "")).strip() or categoria.nome
    categoria.cor = str(form.get("cor", "")).strip() or None
    ordem_raw = str(form.get("ordem", "")).strip()
    categoria.ordem = int(ordem_raw) if ordem_raw else 0
    categoria.identificadores = _parse_identificadores(form.get("identificadores", ""))
    categoria.valor_fixo = _decimal_ou(form.get("valor_fixo"), None)
    categoria.ativo = form.get("ativo") is not None

    session = get_session()
    session.merge(categoria)
    session.commit()
    session.close()

    return RedirectResponse(url=f"/categorias?rateio_id={categoria.rateio_id}&mensagem=Categoria+salva+com+sucesso", status_code=303)


@router.get("/extrato", response_class=HTMLResponse)
async def pagina_extrato(request: Request):
    usuario = exigir_login(request)
    rateios = _rateios_visiveis(usuario)

    rateio_id = int(request.query_params.get("rateio_id", "0") or 0)
    if not rateio_id and rateios:
        rateio_id = rateios[0]["id"]

    rateio = _rateio_acessivel(usuario, rateio_id) if rateio_id else None

    categorias = []
    map_classificacao = {}
    membros = []
    if rateio:
        categorias = listar_categorias(rateio_id)
        map_classificacao = {
            c["codigo_transacao"]: c["categoria_id"]
            for c in listar_classificacao(rateio_id)
        }
        membros = listar_membros_rateio(rateio_id)

    transacoes = []
    if rateio:
        nome_cota = {c["id"]: c["identificador"] for c in listar_cotas(rateio_id)}
        categorias_etiqueta = [c for c in categorias if c.get("ativo")]
        for t in listar_extrato(rateio_id):
            item = {
                "banco": t.banco,
                "data": t.data,
                "transacao": t.transacao,
                "tipo_transacao": t.tipo_transacao,
                "identificacao": t.identificacao,
                "valor": t.valor,
                "codigo_transacao": t.codigo_transacao,
                "eh_debito": t.tipo_transacao == get_transacao_debito(t.banco),
                "categoria_id": map_classificacao.get(t.codigo_transacao),
            }
            item.update(
                montar_etiqueta(item, categorias_etiqueta, map_classificacao, membros, nome_cota=nome_cota)
            )
            transacoes.append(item)

    mensagem = request.query_params.get("mensagem", None)
    return templates.TemplateResponse(
        "extrato.html",
        {
            "request": request,
            "usuario": usuario,
            "rateios": rateios,
            "rateio": rateio.to_dict() if rateio else None,
            "categorias": categorias,
            "membros": membros,
            "transacoes": transacoes,
            "mensagem": mensagem,
        },
    )


@router.post("/extrato/classificar", response_class=HTMLResponse)
async def classificar_extrato(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)
    codigo_transacao = str(form.get("codigo_transacao", "")).strip()
    categoria_id = int(form.get("categoria_id", "0") or 0)
    identificacao = str(form.get("identificacao", "")).strip()
    salvar_identificador = form.get("salvar_identificador") is not None

    if not codigo_transacao or not categoria_id:
        return RedirectResponse(url=f"/extrato?rateio_id={rateio_id}", status_code=303)

    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio:
        return RedirectResponse(url="/extrato", status_code=303)

    salvar_classificacao_manual(rateio_id, codigo_transacao, categoria_id, usuario["id"])

    # Opcionalmente, salva a identificação do pagamento como identificador da categoria.
    if salvar_identificador and identificacao:
        categoria = buscar_categoria(categoria_id)
        if categoria and categoria.rateio_id == rateio_id:
            ids = list(categoria.identificadores or [])
            if identificacao not in ids:
                ids.append(identificacao)
                session = get_session()
                categoria.identificadores = ids
                session.merge(categoria)
                session.commit()
                session.close()

    return RedirectResponse(
        url=f"/extrato?rateio_id={rateio_id}&mensagem=Classificacao+salva+com+sucesso",
        status_code=303,
    )


@router.post("/extrato/vincular-membro", response_class=HTMLResponse)
async def vincular_credito_membro(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)
    membro_id = int(form.get("membro_id", "0") or 0)
    identificacao = str(form.get("identificacao", "")).strip()

    if not membro_id or not identificacao:
        return RedirectResponse(url=f"/extrato?rateio_id={rateio_id}", status_code=303)

    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio:
        return RedirectResponse(url="/extrato", status_code=303)

    membro = buscar_membro(membro_id)
    if not membro:
        return RedirectResponse(url=f"/extrato?rateio_id={rateio_id}", status_code=303)

    cota = buscar_cota(membro.cota_id) if membro.cota_id else None
    if not cota or cota.rateio_id != rateio_id:
        return RedirectResponse(url=f"/extrato?rateio_id={rateio_id}", status_code=303)

    ids = list(membro.identificadores_pagamento or [])
    if identificacao not in ids:
        ids.append(identificacao)
        session = get_session()
        membro.identificadores_pagamento = ids
        session.merge(membro)
        session.commit()
        session.close()

    return RedirectResponse(
        url=f"/extrato?rateio_id={rateio_id}&mensagem=Identificador+salvo+no+membro",
        status_code=303,
    )


@router.post("/extrato/atualizar", response_class=HTMLResponse)
async def atualizar_extrato(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)

    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio:
        return RedirectResponse(url="/extrato", status_code=303)

    try:
        from dto.extrato_request import ExtratoApiRequest
        from service.extrato.pluggy import ExtratoPluggyService

        dados = rateio.to_dict()
        service = ExtratoPluggyService(
            client_id=dados.get("pluggy_client_id"),
            client_secret=dados.get("pluggy_client_secret"),
            account_id=dados.get("pluggy_account_id"),
            rateio_id=dados["id"],
        )
        req = ExtratoApiRequest()
        extrato_dados = service.obter_extrato(req.data_inicial, req.data_final)
        service.gravar_extrato(extrato_dados)
        mensagem = "Extrato atualizado com sucesso."
    except Exception as e:
        mensagem = f"Erro ao atualizar extrato: {e}"

    return RedirectResponse(url=f"/extrato?rateio_id={rateio_id}&mensagem={mensagem}", status_code=303)


@router.get("/fechamentos", response_class=HTMLResponse)
async def pagina_fechamentos(request: Request):
    usuario = exigir_login(request)
    if usuario["perfil"] != "organizador":
        return RedirectResponse(url="/", status_code=303)

    rateios = listar_por_organizador(usuario["id"])
    rateio_id = int(request.query_params.get("rateio_id", "0") or 0)
    if not rateio_id and rateios:
        rateio_id = rateios[0]["id"]

    dashboard = [
        item
        for item in montar_dashboard(usuario=usuario)
        if item["rateio"]["organizador_id"] == usuario["id"]
    ]
    item = next((d for d in dashboard if d["rateio"]["id"] == rateio_id), None)
    if item is None and dashboard:
        item = dashboard[0]

    mensagem = request.query_params.get("mensagem", None)
    from datetime import datetime as _dt

    return templates.TemplateResponse(
        "fechamentos.html",
        {
            "request": request,
            "usuario": usuario,
            "rateios": rateios,
            "rateio": item["rateio"] if item else None,
            "cotas": item["cotas"] if item else [],
            "meses": item["meses"] if item else [],
            "transferencias": item["transferencias"] if item else [],
            "mensagem": mensagem,
            "ano_atual": _dt.now().year,
            "mes_atual": _dt.now().month,
            "meses_nome": [MESES_NOME.get(n, n) for n in range(1, 13)],
        },
    )


@router.post("/fechamentos/fechar", response_class=HTMLResponse)
async def fechar_mes(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)
    mes_numero = int(form.get("mes", "0") or 0)
    ano = int(form.get("ano", "0") or 0)

    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio or not 1 <= mes_numero <= 12 or not ano:
        return RedirectResponse(url="/fechamentos", status_code=303)

    data_inicial = f"01/{mes_numero:02d}/{ano}"
    data_final = _ultimo_dia(mes_numero, ano)
    data_inicial_pag, data_final_pag, mes_nome = _periodo_pagamentos(mes_numero, ano)

    fechar_despesas(
        data_inicial,
        data_final,
        valida_mes=False,
        gerar_cobranca=False,
        rateio_id=rateio_id,
    )
    fechar_pagamentos(data_inicial_pag, data_final_pag, rateio_id=rateio_id, mes=mes_nome, ano=ano)

    return RedirectResponse(
        url=f"/fechamentos?rateio_id={rateio_id}&mensagem=Fechamento+concluido+sem+gerar+cobrancas",
        status_code=303,
    )


@router.post("/fechamentos/gerar-cobranca", response_class=HTMLResponse)
async def gerar_cobrancas(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)
    mes_numero = int(form.get("mes", "0") or 0)
    ano = int(form.get("ano", "0") or 0)

    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio or not 1 <= mes_numero <= 12 or not ano:
        return RedirectResponse(url="/fechamentos", status_code=303)

    data_inicial = f"01/{mes_numero:02d}/{ano}"
    data_final = _ultimo_dia(mes_numero, ano)

    fechar_despesas(
        data_inicial,
        data_final,
        valida_mes=False,
        gerar_cobranca=True,
        rateio_id=rateio_id,
    )

    return RedirectResponse(
        url=f"/fechamentos?rateio_id={rateio_id}&mensagem=Cobrancas+geradas+com+sucesso",
        status_code=303,
    )


@router.post("/fechamentos/sincronizar", response_class=HTMLResponse)
async def sincronizar_pagamentos(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)
    mes_numero = int(form.get("mes", "0") or 0)
    ano = int(form.get("ano", "0") or 0)

    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio or not 1 <= mes_numero <= 12 or not ano:
        return RedirectResponse(url="/fechamentos", status_code=303)

    data_inicial_pag, data_final_pag, mes_nome = _periodo_pagamentos(mes_numero, ano)
    fechar_pagamentos(data_inicial_pag, data_final_pag, rateio_id=rateio_id, mes=mes_nome, ano=ano)

    return RedirectResponse(
        url=f"/fechamentos?rateio_id={rateio_id}&mensagem=Pagamentos+sincronizados",
        status_code=303,
    )


@router.post("/fechamentos/enviar-cobrancas", response_class=HTMLResponse)
async def enviar_cobrancas(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)
    mes_numero = int(form.get("mes", "0") or 0)
    ano = int(form.get("ano", "0") or 0)

    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio or not 1 <= mes_numero <= 12 or not ano:
        return RedirectResponse(url="/fechamentos", status_code=303)

    mes_nome = MESES_NOME.get(mes_numero, mes_numero)
    try:
        cobrar_e_enviar_whatsapp(CobrarRequest(mes=mes_nome, ano=str(ano)))
    except Exception as e:
        return RedirectResponse(
            url=f"/fechamentos?rateio_id={rateio_id}&mensagem=Erro+ao+enviar+cobrancas",
            status_code=303,
        )

    return RedirectResponse(
        url=f"/fechamentos?rateio_id={rateio_id}&mensagem=Cobrancas+enviadas+por+WhatsApp",
        status_code=303,
    )


@router.post("/fechamentos/cobrar-cota", response_class=HTMLResponse)
async def cobrar_cota(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)
    cota_id = int(form.get("cota_id", "0") or 0)
    mes = str(form.get("mes", "")).strip()
    ano = int(form.get("ano", "0") or 0)

    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio or not cota_id or not mes or not ano:
        return RedirectResponse(url=f"/fechamentos?rateio_id={rateio_id}", status_code=303)

    resultado = cobrar_cota_service(mes, ano, cota_id)
    if not resultado["encontrada"]:
        mensagem = "Cobranca+nao+encontrada"
    elif resultado["whatsapp"] and resultado["email"]:
        mensagem = "Cobranca+enviada+por+email+e+WhatsApp"
    elif resultado["email"]:
        mensagem = "Cobranca+enviada+apenas+por+email+(WhatsApp+indisponivel)"
    elif resultado["whatsapp"]:
        mensagem = "Cobranca+enviada+apenas+por+WhatsApp+(email+indisponivel)"
    else:
        mensagem = "Falha+ao+enviar+cobranca"
    return RedirectResponse(
        url=f"/fechamentos?rateio_id={rateio_id}&mensagem={mensagem}",
        status_code=303,
    )


@router.post("/fechamentos/mover-saldo", response_class=HTMLResponse)
async def mover_saldo(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)
    cota_id = int(form.get("cota_id", "0") or 0)
    origem_mes = str(form.get("origem_mes", "")).strip()
    origem_ano = int(form.get("origem_ano", "0") or 0)
    valor = _decimal_ou(form.get("valor"), Decimal("0.00"))

    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio or not cota_id or not origem_mes or not origem_ano or valor <= 0:
        return RedirectResponse(url=f"/fechamentos?rateio_id={rateio_id}", status_code=303)

    destino_valor = str(form.get("destino", "")).strip()
    if "|" in destino_valor:
        destino_mes, destino_ano_str = destino_valor.split("|", 1)
        destino_ano = int(destino_ano_str or 0)
    else:
        destino_mes, destino_ano = destino_valor, 0

    if not destino_mes or not destino_ano:
        return RedirectResponse(url=f"/fechamentos?rateio_id={rateio_id}", status_code=303)
    if destino_mes == origem_mes and destino_ano == origem_ano:
        return RedirectResponse(
            url=f"/fechamentos?rateio_id={rateio_id}&mensagem=Destino+igual+ao+mes+de+origem",
            status_code=303,
        )

    mover_credito(rateio_id, cota_id, origem_mes, origem_ano, destino_mes, destino_ano, valor)

    # Recalcula apenas do mês alterado (mais antigo entre origem/destino) em diante.
    inicio = _mes_mais_antigo(origem_mes, origem_ano, destino_mes, destino_ano)
    recalcular_fechamentos(rateio_id, a_partir_de=inicio)

    return RedirectResponse(
        url=f"/fechamentos?rateio_id={rateio_id}&mensagem=Saldo+movido+para+{destino_mes}/{destino_ano}",
        status_code=303,
    )


@router.post("/fechamentos/remover-transferencia", response_class=HTMLResponse)
async def remover_transferencia(request: Request):
    usuario = exigir_login(request)
    form = await request.form()
    rateio_id = int(form.get("rateio_id", "0") or 0)
    credito_id = int(form.get("credito_id", "0") or 0)

    rateio = _rateio_do_organizador(usuario, rateio_id)
    if not rateio or not credito_id:
        return RedirectResponse(url=f"/fechamentos?rateio_id={rateio_id}", status_code=303)

    credito = buscar_credito(credito_id)
    if not credito:
        return RedirectResponse(
            url=f"/fechamentos?rateio_id={rateio_id}&mensagem=Transferencia+nao+encontrada",
            status_code=303,
        )

    origem_mes = credito.origem_mes
    origem_ano = credito.origem_ano
    destino_mes = credito.destino_mes
    destino_ano = credito.destino_ano

    removido = remover_credito(credito_id)
    if removido:
        # Recalcula apenas do mês alterado (mais antigo entre origem/destino) em diante.
        inicio = _mes_mais_antigo(origem_mes, origem_ano, destino_mes, destino_ano)
        recalcular_fechamentos(rateio_id, a_partir_de=inicio)
        mensagem = "Transferencia+removida+com+sucesso"
    else:
        mensagem = "Transferencia+nao+encontrada"

    return RedirectResponse(
        url=f"/fechamentos?rateio_id={rateio_id}&mensagem={mensagem}",
        status_code=303,
    )
