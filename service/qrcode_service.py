import re
from datetime import datetime
from unicodedata import normalize

from pypix.pix import Pix

from dto.pix import PixRequest
from repository.cobranca import Cobranca
from service.bucket import enviar_base64


def _sanitize_txid(value, max_len=25):
    """Gera um txid (identificador PIX) válido: apenas [A-Za-z0-9], sem espaços
    ou acentos, com no máximo max_len caracteres."""
    if not value:
        value = f"T{datetime.now().strftime('%Y%m%d%H%M%S')}"
    texto = normalize("NFD", str(value)).encode("ascii", "ignore").decode("ascii")
    texto = re.sub(r"[^A-Za-z0-9]", "", texto)
    texto = texto[:max_len] if len(texto) > max_len else texto
    return texto or "TXID"


def generate_qrcode(pix_data: PixRequest) -> dict:
    pix = Pix()
    pix.set_name_receiver(pix_data.name_receiver)
    pix.set_city_receiver(pix_data.city_receiver)
    pix.set_key(pix_data.key)
    pix.set_identification(_sanitize_txid(pix_data.identification))
    pix.set_zipcode_receiver(pix_data.zipcode_receiver)
    pix.set_description(pix_data.description)
    # O campo 54 (valor) do BR Code usa ponto decimal e 2 casas (ex.: "100.00").
    pix.set_amount(pix_data.amount)

    base64qr = pix.save_qrcode(
        output='./qrcode.png',
        box_size=7,
        border=1,
    )

    current_date = datetime.now().strftime("%Y%m%d%H%M%S")
    nome_arquivo = f"qrcode-{_sanitize_txid(pix_data.identification)}-{current_date}.png"
    enviar_base64("qrcodepix", base64qr.replace("data:image/png;base64,", ""), nome_arquivo, "image/png")

    return {'qrcode': base64qr, 'br_code': pix.get_br_code(), 'nome_arquivo': nome_arquivo}


def gerar_salvar_qrcode(mes, ano, cota, identification, description, amount, data_atual=None, cota_id=None, membro_id=None):
    pix = PixRequest(
        name_receiver='Cauê Beloni',
        city_receiver='Santo André',
        key='11986768497',
        identification=identification,
        zipcode_receiver='09291250',
        description=description,
        amount=amount
    )
    pix_response = generate_qrcode(pix)
    cobranca = Cobranca(
        mes=mes,
        ano=ano,
        cota=cota,
        cota_id=cota_id,
        membro_id=membro_id,
        valor=amount,
        brcode=pix_response.get("br_code"),
        qrcode=pix_response.get("qrcode"),
        url_qrcode=pix_response.get("nome_arquivo"),
        data_atual=data_atual
    )
    cobranca.save()
