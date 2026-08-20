
import logging
from datetime import datetime
from pydantic import BaseModel, Field

from util.datas_uteis import (
    first_day_of_current_month,
    last_day_of_current_month,
    last_day_of_previous_month,
    meses_portugues,
)

class FechamentoRequest(BaseModel):
    data_inicial: str = Field(default_factory=last_day_of_previous_month)
    data_final: str = Field(default_factory=last_day_of_current_month)

class FechamentoPagamentosDate():
    """Janela padrão usada pela cron /fechamento-pagamentos.

    Fecha o mês ANTERIOR ao corrente usando os recebimentos do mês corrente,
    seguindo o modelo de negócio: o fechamento do mês M é pago em M+1.

    Ex.: em agosto, fecha JULHO considerando os recebimentos de agosto
    (01/08 até o fim do mês). Isso não depende da última cobrança, evitando
    que a cron reabra um mês antigo (dupla contagem do dia do fechamento)
    quando ainda não existe cobrança do mês corrente.
    """

    def __init__(self):
        hoje = datetime.now()

        if hoje.month == 1:
            mes_fechamento, self.ano = 12, hoje.year - 1
        else:
            mes_fechamento, self.ano = hoje.month - 1, hoje.year

        self.mes = meses_portugues[datetime(self.ano, mes_fechamento, 1).strftime("%B")]

        # Janela de recebimentos: primeiro até o último dia do mês corrente.
        self.data_inicial = f"01/{hoje.month:02d}/{hoje.year}"
        self.data_final = last_day_of_current_month()

        logging.info(
            f"Fechamento de pagamentos: fechando {self.mes}/{self.ano} com "
            f"recebimentos de {self.data_inicial} até {self.data_final}"
        )


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
