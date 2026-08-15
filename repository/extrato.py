from datetime import datetime
from typing import Optional

from config.database import criar_conexao
from pydantic import BaseModel


class Extrato(BaseModel):
    banco: str
    data: str
    transacao: str
    tipo_transacao: str
    identificacao: str
    valor: float
    codigo_transacao: str = ""
    rateio_id: Optional[int] = None

    def __init__(self, banco, data, transacao, tipo_transacao, identificacao, valor, codigo_transacao="", rateio_id=None):
        super().__init__(
            banco=banco,
            data=data,
            transacao=transacao,
            tipo_transacao=tipo_transacao,
            identificacao=identificacao,
            valor=valor,
            codigo_transacao=codigo_transacao,
            rateio_id=rateio_id,
        )


class ExtratoRepository:
    def __init__(self):
        self.db = criar_conexao()

    def salvar(self, registro: Extrato):
        cursor = self.db.cursor()

        # Evita duplicar a mesma transação ao atualizar o extrato mais de uma vez.
        if registro.codigo_transacao:
            if registro.rateio_id is not None:
                cursor.execute(
                    "SELECT id FROM extrato WHERE codigo_transacao = %s AND rateio_id = %s LIMIT 1",
                    (registro.codigo_transacao, registro.rateio_id),
                )
            else:
                cursor.execute(
                    "SELECT id FROM extrato WHERE codigo_transacao = %s AND rateio_id IS NULL LIMIT 1",
                    (registro.codigo_transacao,),
                )
            if cursor.fetchone():
                return

        query = """
        INSERT INTO extrato (banco, data, transacao, tipo_transacao, identificacao, valor, codigo_transacao, rateio_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        date_formatted = datetime.strptime(registro.data, "%d/%m/%Y").strftime("%Y-%m-%d")
        values = (
            registro.banco,
            date_formatted,
            registro.transacao,
            registro.tipo_transacao,
            registro.identificacao,
            registro.valor,
            registro.codigo_transacao,
            registro.rateio_id,
        )
        cursor.execute(query, values)
        self.db.commit()

    def consultar(self, data_inicio: str, data_fim: str, rateio_id: Optional[int] = None) -> list[Extrato]:
        cursor = self.db.cursor()
        query = """
        SELECT banco, data, transacao, tipo_transacao, identificacao, valor, codigo_transacao, rateio_id
        FROM extrato
        WHERE data BETWEEN %s AND %s
        """
        params: list = [
            datetime.strptime(data_inicio, "%d/%m/%Y").strftime("%Y-%m-%d"),
            datetime.strptime(data_fim, "%d/%m/%Y").strftime("%Y-%m-%d"),
        ]
        if rateio_id is not None:
            query += " AND (rateio_id = %s OR rateio_id IS NULL)"
            params.append(rateio_id)

        cursor.execute(query, params)
        resultados = cursor.fetchall()
        return [
            Extrato(
                banco=row[0],
                data=row[1].strftime("%d/%m/%Y"),
                transacao=row[2],
                tipo_transacao=row[3],
                identificacao=row[4],
                valor=row[5],
                codigo_transacao=row[6],
                rateio_id=row[7],
            )
            for row in resultados
        ]

    def consultar_tipo_transacao(
        self, data_inicio: str, data_fim: str, tipo_transacao: str, rateio_id: Optional[int] = None
    ) -> list[Extrato]:
        cursor = self.db.cursor()
        query = """
        SELECT banco, data, transacao, tipo_transacao, identificacao, valor, codigo_transacao, rateio_id
        FROM extrato
        WHERE data BETWEEN %s AND %s
        AND tipo_transacao = %s
        """
        params: list = [
            datetime.strptime(data_inicio, "%d/%m/%Y").strftime("%Y-%m-%d"),
            datetime.strptime(data_fim, "%d/%m/%Y").strftime("%Y-%m-%d"),
            tipo_transacao,
        ]
        if rateio_id is not None:
            query += " AND (rateio_id = %s OR rateio_id IS NULL)"
            params.append(rateio_id)

        cursor.execute(query, params)
        resultados = cursor.fetchall()
        return [
            Extrato(
                banco=row[0],
                data=row[1].strftime("%d/%m/%Y"),
                transacao=row[2],
                tipo_transacao=row[3],
                identificacao=row[4],
                valor=row[5],
                codigo_transacao=row[6],
                rateio_id=row[7],
            )
            for row in resultados
        ]


def criar_tabela_extrato():
    """Cria a tabela de extrato caso ainda não exista."""
    db = criar_conexao()
    cursor = db.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS extrato (
            id INT AUTO_INCREMENT PRIMARY KEY,
            banco VARCHAR(50),
            data DATE,
            transacao VARCHAR(255),
            tipo_transacao VARCHAR(50),
            identificacao VARCHAR(255),
            valor DECIMAL(10, 2),
            codigo_transacao VARCHAR(255),
            rateio_id INT NULL
        )
        """
    )
    db.commit()
    db.close()


def listar_por_rateio(rateio_id: Optional[int] = None) -> list[Extrato]:
    """Lista o extrato de um rateio (ou todo o extrato quando rateio_id é None)."""
    db = criar_conexao()
    cursor = db.cursor()
    query = """
    SELECT banco, data, transacao, tipo_transacao, identificacao, valor, codigo_transacao, rateio_id
    FROM extrato
    """
    params: list = []
    if rateio_id is not None:
        query += " WHERE (rateio_id = %s OR rateio_id IS NULL)"
        params.append(rateio_id)
    query += " ORDER BY data DESC, id DESC"

    cursor.execute(query, params)
    resultados = cursor.fetchall()
    db.close()
    return [
        Extrato(
            banco=row[0],
            data=row[1].strftime("%d/%m/%Y"),
            transacao=row[2],
            tipo_transacao=row[3],
            identificacao=row[4],
            valor=row[5],
            codigo_transacao=row[6],
            rateio_id=row[7],
        )
        for row in resultados
    ]
