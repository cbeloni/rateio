import logging

from service.send_whatsapp import send_whatsapp_message, send_whatsapp_image
    
def enviar_cobranca_whatsapp(telefone: str, mensagem: str, imagem_url: str, pix_code: str) -> None:
    send_whatsapp_message(telefone, mensagem)
    # send_whatsapp_image(telefone, imagem_url, caption=pix_code)
    try:
        send_whatsapp_image(telefone, imagem_url)
    except Exception as e:
        logging.error(
            "Falha ao enviar imagem no WhatsApp para o telefone %s e url %s: %s",
            telefone,
            imagem_url,
            e,
            exc_info=True,
        )
