def montar_messagem_whatsapp(rateios: list[dict]) -> list[str]:
    mensagens = []
    for item in rateios:
        rateio = item.get("rateio", {})
        meses = item.get("meses", [])
        if not meses:
            continue

        ultimo = meses[0]
        mensagem = f"*Rateio: {rateio.get('nome')}*\n"
        mensagem += f"*Referente a {ultimo['mes']}/{ultimo['ano']}*\n"
        mensagem += f"*Despesas:* R$ {float(ultimo['total']):.2f}\n"
        for nome, valor in ultimo.get("despesas", {}).items():
            mensagem += f"- *{nome}:* R$ {float(valor):.2f}\n"

        mensagem += "*Pagamentos realizados:*\n"
        for cota in ultimo.get("cotas", []):
            mensagem += f"- *{cota['identificador']}:* R$ {float(cota['pagamentos']):.2f}\n"

        mensagens.append(mensagem.strip())

    return mensagens
