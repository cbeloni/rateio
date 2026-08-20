# Plano — Coluna de Etiqueta no Extrato

> ✅ **Implementado em 2026-08-20** (`service/extrato/etiqueta.py`,
> `api/rotas/gestao.py::pagina_extrato`, `templates/extrato.html`).
>
> Documento de planejamento. A feature é **somente leitura** (exibição): não
> altera nenhum registro no banco.

---

## 1. Objetivo

Na tela **Extrato** (`GET /extrato` → `templates/extrato.html`), adicionar uma coluna
**"Etiqueta"** que mostra, para cada lançamento, se ele **já está reconhecido** pelo
sistema — ou seja:

- se o **identificador** do lançamento (`identificacao`) casa com algum **identificador salvo**
  (de categoria, para débitos; de membro, para créditos), **ou**
- se o `codigo_transacao` já tem uma **classificação manual salva** (`classificacao_manual`).

A coluna também **exibe o(s) identificador(es)** que casaram e usa **cores** para distinguir
os estados de reconhecimento.

Isso dá visibilidade imediata sobre o que ainda precisa de configuração antes do fechamento,
sem precisar abrir categoria/membro.

---

## 2. Estados da etiqueta (e cores)

| Estado | Significado | Badge / cor | Exemplo |
|---|---|---|---|
| **Identificado por identificador** | O texto da `identificacao` contém um termo de `identificadores` de uma **categoria** (débito) ou de `identificadores_pagamento` de um **membro** (crédito) | `bg-success` (verde) — ou usar a `cor` da categoria quando existir | "SABESP" → categoria *Sabesp* (id. `sabesp`) |
| **Regra salva (classificação manual)** | O `codigo_transacao` tem registro em `classificacao_manual` → categoria (débito) | `bg-primary` (azul) | código `b0ecced1…` → categoria *Enel* |
| **Sem etiqueta** | Nenhum identificador casou e não há regra manual | `bg-secondary` (cinza) — opcional `bg-danger` p/ destaque de pendência | transação nova sem vínculo |

Regras de prioridade (espelham `fechar_despesas` / `fechar_pagamentos`):

1. **Débito**: `classificacao_manual` (por `codigo_transacao`) tem prioridade sobre o
   match por identificadores de categoria.
2. **Crédito**: match por `identificadores_pagamento` dos membros.

---

## 3. O que a etiqueta mostra

Cada etiqueta exibe (em texto curto, ex.: `Sabesp · "sabesp"`):

- o **alvo** reconhecido (nome da categoria ou nome do membro/cota), e
- o **identificador** que casou (entre aspas), para conferência.

Exemplos na coluna:

| Identificação | Tipo | Etiqueta |
|---|---|---|
| `SABESP` | Débito | `🟢 Sabesp · "sabesp"` |
| `ENEL DISTRIBUICAO SAO PAULO` (codigo com regra manual) | Débito | `🔵 Enel · regra salva` |
| `ANA CAROLINA DA SILVA MARTINS` | Crédito | `🟢 AP2 · Ana Carolina · "ana carolina"` |
| `PIX Marketplace` | Débito | `⚪ sem etiqueta` |

---

## 4. Dados e regras de casamento (backend — `pagina_extrato`)

Fontes de dados já disponíveis na rota `api/rotas/gestao.py::pagina_extrato`:

- `categorias = listar_categorias(rateio_id)` → cada item tem `id`, `nome`, `cor`, `identificadores` (lista).
- `map_classificacao = {c["codigo_transacao"]: c["categoria_id"] for c in listar_classificacao(rateio_id)}`.
- `membros = listar_membros_rateio(rateio_id)` → cada item tem `id`, `nome`, `cota_id`, `identificadores_pagamento` (lista).

Para cada transação `t` (do `listar_extrato(rateio_id)`):

1. **Débito** (`t.tipo_transacao == get_transacao_debito(t.banco)`):
   - Se `t.codigo_transacao in map_classificacao` → etiqueta **regra salva** (`bg-primary`),
     texto com o nome da categoria (buscar em `categorias` por `map_classificacao[codigo]`).
   - Senão, varrer `categorias` e checar se algum termo de `identificadores` está contido em
     `t.identificacao` (case-insensitive) → etiqueta **identificado por identificador**
     (`bg-success`), texto `Categoria · "termo"`.
   - Senão → **sem etiqueta** (`bg-secondary`).
2. **Crédito** (senão): varrer `membros` e checar se algum termo de `identificadores_pagamento`
   está contido em `t.identificacao` (case-insensitive) → etiqueta **identificado**
   (`bg-success`), texto `Cota · Membro · "termo"`. Senão → **sem etiqueta**.

Campos adicionados ao dict `t` (para o template):

```python
t["etiqueta_tipo"]      # "identificado" | "regra_salva" | "sem_etiqueta"
t["etiqueta_texto"]     # ex.: 'Sabesp · "sabesp"'  /  'Enel · regra salva'  /  'sem etiqueta'
t["etiqueta_classe"]    # "bg-success" | "bg-primary" | "bg-secondary"   (ou cor da categoria)
t["etiqueta_identificador"]  # termo que casou (para tooltip/detalhe), quando houver
```

> Sugestão: extrair a lógica de match num helper (ex.: `service/extrato/etiqueta.py` com
> `montar_etiqueta(transacao, categorias, map_classificacao, membros)`) para ficar testável
> e espelhar exatamente as regras usadas no fechamento.

---

## 5. Frontend — `templates/extrato.html`

- Adicionar `<th>Etiqueta</th>` no `thead`.
- No `tbody`, adicionar um `<td>` com um badge:

```html
<td>
  {% if t.etiqueta_tipo == 'sem_etiqueta' %}
    <span class="badge bg-secondary" title="Sem identificador salvo">sem etiqueta</span>
  {% else %}
    <span class="badge {{ t.etiqueta_classe }}" title="{{ t.etiqueta_identificador or '' }}">
      {{ t.etiqueta_texto }}
    </span>
  {% endif %}
</td>
```

- Manter as colunas/ações atuais (classificar débito / vincular crédito) intactas.
- Dica visual (opcional): usar a **cor da categoria** (`bg-…` ou estilo inline com `t.cor`)
  quando a etiqueta for "identificado por identificador", para reforçar o vínculo visual.

---

## 6. Casos de teste

1. Débito com termo de `identificadores` da categoria na `identificacao` → verde + nome do termo.
2. Débito com `codigo_transacao` em `classificacao_manual` (mesmo sem match por texto) → azul.
3. Débito sem identificador e sem regra manual → cinza "sem etiqueta".
4. Crédito com termo de `identificadores_pagamento` do membro → verde + membro/cota + termo.
5. Crédito sem identificador → cinza "sem etiqueta".
6. Case-insensitive: `sabesp` casa com `SABESP`, `Sabesp`, etc.
7. Prioridade: débito com `classificacao_manual` **e** match por texto → mostra azul (regra salva).

---

## 7. Fora de escopo (nesta etapa)

- Não altera tabelas nem registros (somente exibição).
- Não muda o algoritmo de fechamento (`fechar_despesas` / `fechar_pagamentos`).
- Não cria botões/ações novas além das já existentes na tela.
