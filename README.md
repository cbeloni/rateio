# Rateio Online API

API em FastAPI para rateio de contas (despesas, fundo, fechamento mensal) e integrações (e-mail, WhatsApp, Google Drive, Pluggy e PagBank).

## Requisitos

- Python `3.12`
- `pipenv` instalado globalmente
- MySQL acessível (para rotas que usam banco)
- Opcional: Docker + Docker Compose

## Como iniciar (local)

1. Criar arquivo de ambiente:

```bash
cp .env.template .env
```

2. Preencher no `.env` ao menos as credenciais de banco:

```env
HOST=...
USER=...
PASSWORD=...
DATABASE=...
```

3. Instalar dependências:

```bash
pipenv install --dev
```

4. Subir a API:

```bash
pipenv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

5. Acessar:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Como iniciar (Docker)

```bash
docker compose up --build
```

A API ficará em `http://localhost:8001` (porta `8001` no host mapeada para `8000` no container).

## Variáveis de ambiente

### Obrigatórias para rotas com banco

- `HOST`
- `USER`
- `PASSWORD`
- `DATABASE`

### Obrigatórias por integração/rota

- `IMAP_EMAIL`, `IMAP_PASSWORD`
  - Usadas em: `/mail`, `/send-email`, `/cobrar`
- `API_KEY`, `FOLDER_ID`
  - Usadas em: `/drive`
- `WHATSAPP_USER`, `WHATSAPP_PASS`, `WHATSAPP_API_URL`
  - Usadas em: `/send-whatsapp`, `/cobrar-whatsapp`
- `PLUGGY_CLIENT_ID`, `PLUGGY_CLIENT_SECRET`
  - Usadas em: `/extrato` com provider `pluggy` (default)
  - Podem ser **sobrescritas por rateio** no cadastro do rateio (junto com `PLUGGY_ACCOUNT_ID`)
- `PAGBANK_USER`, `PAGBANK_TOKEN`
  - Usadas em: `/movimentos-pagbank`
- `MERCADOPAGO_COOKIE`
  - Usada em: `/extrato` com provider `mercadopago`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `ENDPOINT_URL`
  - Usadas em operações de upload em bucket (fluxos de fechamento)

### Opcionais

- `PLUGGY_BASE_URL` (default: `https://api.pluggy.ai`)
- `PLUGGY_PAGE_SIZE` (default: `500`)

## Observações importantes

- A API pode iniciar sem todas as variáveis preenchidas, mas endpoints que dependem delas irão falhar em runtime.
- O endpoint `/` consulta banco para montar o dashboard HTML (`templates/home.html`).

## Estrutura principal

- `main.py`: definição das rotas FastAPI
- `config/database.py`: conexão síncrona MySQL
- `repository/`: acesso a dados
- `service/`: regras de negócio e integrações
- `dto/`: modelos de entrada/saída
