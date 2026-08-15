
import logging
from datetime import datetime
from pydantic import BaseModel, Field

from repository.cobranca import get_last_cobranca
from util.datas_uteis import first_day_of_current_month, last_day_of_current_month, last_day_of_previous_month

class FechamentoRequest(BaseModel):
    data_inicial: str = Field(default_factory=last_day_of_previous_month)
    data_final: str = Field(default_factory=last_day_of_current_month)

class FechamentoPagamentosDate():
    def __init__(self):
        ultimo_fechamento = get_last_cobranca()
        data_atual = getattr(ultimo_fechamento, "data_atual", None) if ultimo_fechamento else None
        logging.info(f"Data atual do último fechamento de despesas: {data_atual}")

        if isinstance(data_atual, datetime):
            self.data_inicial = data_atual.strftime("%d/%m/%Y")
        elif isinstance(data_atual, str) and data_atual.strip():
            data_atual = data_atual.strip()
            self.data_inicial = self._normalizar_data(data_atual)
        else:
            self.data_inicial = last_day_of_previous_month()

        logging.info(f"Data inicial do fechamento de pagamentos: {self.data_inicial}")
        self.data_final: str = last_day_of_current_month()
        logging.info(f"Data final do fechamento de pagamentos: {self.data_final}")

    @staticmethod
    def _normalizar_data(data: str) -> str:
        formatos = ("%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S")
        for formato in formatos:
            try:
                return datetime.strptime(data, formato).strftime("%d/%m/%Y")
            except ValueError:
                continue
        return last_day_of_previous_month()


class FechamentoDespesasRequest(BaseModel):
    data_inicial: str = Field(default_factory=first_day_of_current_month)
    data_final: str = Field(default_factory=last_day_of_current_month)
    valida_mes: bool = True
    

def get_transacao_debito(banco: str) -> dict:
    transacao_map = {
        'cora': 'DÉBITO',
        'bb': 'Saída',
        'pagbank': 'Saída',
        "pluggy": 'DEBIT',
    }
    return transacao_map.get(banco, 'DÉBITO')


def get_transacao_credito(banco: str) -> dict:
    transacao_map = {
        'cora': 'CRÉDITO',
        'bb': 'Entrada',
        'pagbank': 'Entrada',
        "pluggy": 'CREDIT'
    }
    return transacao_map.get(banco, 'CRÉDITO')
