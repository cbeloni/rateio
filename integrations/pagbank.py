import requests
import os
from dotenv import load_dotenv
import base64

from dto.pagbank_request import MovimentosPagbankParams

load_dotenv()

def consultar_movimentos_pagbank(movimentos_pagbank_params: MovimentosPagbankParams) -> requests.Response:
    user = os.getenv("PAGBANK_USER")
    token = os.getenv("PAGBANK_TOKEN")

    if not user or not token:
        print("Erro: As variáveis de ambiente PAGBANK_USER e PAGBANK_TOKEN não foram definidas.")
        return None

    base_url = "https://edi.api.pagbank.com.br/edi/v1/2.01/movimentos"
    

    # Criar o token de autorização Basic
    auth_string = f"{user}:{token}"
    auth_bytes = auth_string.encode('ascii')
    base64_bytes = base64.b64encode(auth_bytes)
    base64_auth_string = base64_bytes.decode('ascii')

    headers = {
        "Authorization": f"Basic {base64_auth_string}"
    }

    try:
        response = requests.get(base_url, headers=headers, params=movimentos_pagbank_params.to_dict())
        response.raise_for_status()  # Lança uma exceção para respostas de erro (4xx ou 5xx)
        return response
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Detalhes do erro: {e.response.text}")
        return None

if __name__ == '__main__':
    # Exemplo de uso (crie um arquivo .env com PAGBANK_USER e PAGBANK_TOKEN)
    # Exemplo de .env:
    # PAGBANK_USER=seu_user_aqui
    # PAGBANK_TOKEN=seu_token_aqui

    data_mov = "2025-06-13"
    pagina = 1
    tamanho_pagina = 10
    tipo_mov = 2

    print(f"Consultando movimentos para {data_mov}, página {pagina}, {tamanho_pagina} itens, tipo {tipo_mov}...")
    resposta = consultar_movimentos_pagbank(data_mov, pagina, tamanho_pagina, tipo_mov)

    if resposta:
        print(f"Status Code: {resposta.status_code}")
        try:
            print("Resposta JSON:")
            print(resposta.json())
        except requests.exceptions.JSONDecodeError:
            print("Resposta (não JSON):")
            print(resposta.text)
    else:
        print("Não foi possível obter uma resposta.")
    