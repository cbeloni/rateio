import logging
import os
from datetime import datetime
from typing import Optional

import requests
from dotenv import load_dotenv

from repository.extrato import Extrato, ExtratoRepository
from service.extrato.extrato_abstract import ExtratoAbstract

load_dotenv()

DEFAULT_BASE_URL = os.getenv('PLUGGY_BASE_URL', 'https://api.pluggy.ai')
DEFAULT_PAGE_SIZE = os.getenv('PLUGGY_PAGE_SIZE', 500)


class ExtratoPluggyService(ExtratoAbstract):
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        base_url: Optional[str] = None,
        page_size: Optional[int] = None,
        rateio_id: Optional[int] = None,
    ):
        self.client_id = client_id or os.getenv('PLUGGY_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('PLUGGY_CLIENT_SECRET')
        self.account_id = account_id or os.getenv('PLUGGY_ACCOUNT_ID')
        self.base_url = base_url or DEFAULT_BASE_URL
        self.page_size = page_size or DEFAULT_PAGE_SIZE
        self.rateio_id = rateio_id

    def _obter_token(self) -> Optional[str]:
        url = f"{self.base_url}/auth"
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
        }
        data = {
            'clientId': self.client_id,
            'clientSecret': self.client_secret,
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json().get('apiKey')

    def obter_extrato(self, data_inicial: str, data_final: str) -> list[dict]:
        api_key = self._obter_token()
        if not api_key:
            raise Exception("Failed to obtain API key from Pluggy.")

        if not self.account_id:
            raise Exception("Pluggy account_id não configurado para este rateio.")

        url = f"{self.base_url}/transactions"
        headers = {
            'accept': 'application/json',
            'x-api-key': api_key,
        }
        params = {
            'accountId': self.account_id,
            'pageSize': self.page_size,
            'from': data_inicial,
            'to': data_final,
        }

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def gravar_extrato(self, extrato: list[dict]) -> None:
        extrato_repository = ExtratoRepository()
        for item in extrato["results"]:
            date_str = item.get('date')
            formatted_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime('%d/%m/%Y') if date_str else ''

            extrato_item = Extrato(
                banco="pluggy",
                data=formatted_date,
                transacao=item.get('operationType', ''),
                tipo_transacao=item.get('type', ''),
                identificacao=item.get('description', ''),
                valor=float(item.get('amount', 0.0)),
                codigo_transacao=item.get('id', ''),
                rateio_id=self.rateio_id,
            )
            try:
                extrato_repository.salvar(extrato_item)
            except Exception as e:
                logging.error(f"Erro ao salvar extrato: {e}")
