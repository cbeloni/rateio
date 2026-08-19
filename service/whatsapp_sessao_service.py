"""Integração com o whatsapp-bot para gerenciar sessões multi-QR (uma por usuário)."""
import base64
import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

WHATSAPP_API = (os.getenv("WHATSAPP_API_URL") or "").rstrip("/")
USER = os.getenv("WHATSAPP_USER")
PASSWORD = os.getenv("WHATSAPP_PASS")

TIMEOUT = 20


class WhatsAppBotError(Exception):
    """Erro ao comunicar com o whatsapp-bot."""


def _headers() -> dict:
    if not USER or not PASSWORD:
        return {}
    auth = f"{USER}:{PASSWORD}"
    auth_b64 = base64.b64encode(auth.encode()).decode()
    return {"Authorization": f"Basic {auth_b64}"}


def _request(method: str, path: str, payload: dict | None = None) -> dict:
    if not WHATSAPP_API:
        raise WhatsAppBotError("WHATSAPP_API_URL não configurada no .env.")

    url = f"{WHATSAPP_API}{path}"
    try:
        response = requests.request(
            method,
            url,
            json=payload,
            headers=_headers(),
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.exception("Falha de conexão com o whatsapp-bot (%s %s).", method, path)
        raise WhatsAppBotError(f"Falha de conexão com o whatsapp-bot: {exc}") from exc

    try:
        data = response.json()
    except ValueError:
        data = {"error": response.text or "Resposta inválida do whatsapp-bot."}

    if response.status_code >= 400:
        detail = data.get("error") or data.get("details") or f"HTTP {response.status_code}"
        raise WhatsAppBotError(str(detail))

    return data


def criar_sessao(session_id: str) -> dict:
    """Cria (ou garante) a sessão do usuário no bot. Retorna o status atual."""
    return _request("POST", "/sessions", {"sessionId": session_id})


def obter_qrcode(session_id: str) -> dict:
    """Retorna o QR Code atual da sessão (ou None) e o status de conexão."""
    return _request("GET", f"/sessions/{session_id}/qrcode")


def obter_status(session_id: str) -> dict:
    """Retorna o status de conexão da sessão."""
    return _request("GET", f"/sessions/{session_id}/status")


def excluir_sessao(session_id: str) -> dict:
    """Encerra e remove a sessão no bot."""
    return _request("DELETE", f"/sessions/{session_id}")
