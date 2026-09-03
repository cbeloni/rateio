# Plano (v2): Categorias com valor fixo e responsável por categoria

> Data: 2026-08-15 · Ambiente: produção (outro ambiente)
> Contexto: Alexandre paga o fundo (R$ 100) no dia 1 de cada mês. A regra "fechamento do mês M = créditos do mês M+1" está correta e deve ser mantida.

---

## 1. Requisito (clarificado)

1. Uma **categoria** pode ter **valor fixo** (mensal, não vem do extrato) OU ser **débito do extrato**.
2. Ao criar a categoria, é possível definir um **membro responsável** por ela (opcional) — um membro específico de uma cota.
3. O **fundo** é apenas um caso: uma categoria com valor fixo (R$ 100), atribuída a um membro.
4. Exemplos: criar uma categoria **"investimento"** (valor fixo, paga por um membro ou não); definir que a categoria **"faxina"** (extrato) é paga por um membro específico de uma cota.
5. O **restante** (sem responsável marcado) é pago pelo **membro principal** da cota — a cota **não é dividida** entre todos os membros.
6. **Marcação do membro principal**: cada cota tem um **membro principal**, que é quem **recebe as mensagens com o QR Code** de pagamento.

---

## 2. Solução recomendada (A): tabela de responsabilidades

### 2.1 Modelo de dados

1. **`categorias`** ganha `valor_fixo` (DECIMAL, nullable):
   - preenchido → categoria de **valor fixo mensal** (não vem do extrato; ex.: fundo, investimento);
   - vazio → categoria de **débito do extrato** (ex.: faxina, ENEL).
   A categoria "fundo" é criada uma vez por rateio, com `valor_fixo = 100` (por cota).

2. **Nova tabela `responsabilidades`**:
   - `id`
   - `rateio_id`
   - `membro_id`
   - `categoria_id` — referência à categoria (fixa ou de extrato).
   - `valor` — **nullable**; `NULL` significa "assume o valor integral" da categoria.
   - `ativo`

3. O fundo deixa de ser configurado no `rateio` e na `cota`; passa a ser uma categoria fixa.

4. **`cobrancas`** ganha `membro_id` (nullable): a cobrança pode ser **por cota** (padrão, restante) ou **por membro** (quando há responsável).

5. **Membro principal**: campo `membro.principal` (boolean, um por cota). É quem paga as obrigações gerais da cota e quem **recebe a mensagem com o QR Code**.

### 2.2 Lógica mensal

1. **Despesas** (categorias sem `valor_fixo`): como hoje — extrato → categorias → total → parcela por cota.
2. **Fixas** (categorias com `valor_fixo`): valor fixo mensal adicionado (por cota); não vêm do extrato.
3. **Geração de QR** (por cota):
   - Para cada `responsabilidade` dos membros da cota:
     - categoria **fixa** (fundo/investimento) → QR do membro com `valor` (ou o valor fixo integral).
     - categoria **de extrato** (faxina/ENEL) → QR do membro com `valor` (ou a parcela da categoria na cota).
   - **Restante** = `parcela + fixas − soma(atribuído)` → QR enviado ao **membro principal** da cota.
   - As mensagens (WhatsApp/e-mail) vão para o **membro principal** (restante) e para o **membro responsável** (categoria atribuída).

### 2.3 Casamento de pagamentos

- O crédito do extrato continua sendo casado por identificadores, mas passa a poder ser associado ao **membro responsável** (para conferir se ele pagou a categoria/fundo dele).
- Ex.: o crédito de R$ 100 do Alexandre no dia 1 é reconhecido como pagamento da categoria fixa **fundo** da cota dele.

---

## 3. Solução alternativa (B): campo simples no membro

- Adicionar `membro.categoria_responsavel_id` (uma categoria) + `membro.valor_responsavel`.
- Mais simples, porém **não suporta**:
  - divisão entre membros (fundo 50/50, por exemplo);
  - mais de uma categoria por membro;
  - generalização limpa para novas categorias.

---

## 4. Comparação

| Critério | A (tabela de responsabilidades) | B (campo no membro) |
|----------|---------------------------------|---------------------|
| Divisão do fundo entre membros | ✅ sim | ❌ não |
| Múltiplas categorias por membro | ✅ sim | ❌ não |
| Generaliza para novas categorias | ✅ sim | ⚠️ parcial |
| Complexidade de implementação | média | baixa |
| Impacto na cobrança (QR por membro) | necessário | parcial |

---

## 5. Recomendação

Adotar a **Solução A (tabela `responsabilidades`)**, pois atende integralmente o requisito (categorias fixas ou de extrato atribuídas a membros específicos, com divisão opcional), mesmo com maior complexidade.

---

## 6. Riscos / pontos de atenção

1. **Categoria fixa não é despesa**: categorias com `valor_fixo` **não** entram no "total de despesas"/parcela (são obrigações fixas separadas). Cuidado para não somá-las junto com as despesas.
2. **QR por membro**: `cobrancas.membro_id` afeta `service/fechamento_despesas.py`, `service/cobrar_service.py` (contato por membro) e a tela de fechamentos.
3. **Casamento de pagamento**: o crédito do dia 1 (Alexandre) precisa ser reconhecido como pagamento da categoria fixa (fundo) — senão aparece como "pagamento comum" e a categoria fica em aberto.
4. **Migração**: criar a categoria "fundo" (valor_fixo 100); remover a configuração antiga de fundo do rateio e das cotas; converter o `valor_fixo` do Alexandre em `responsabilidade` de fundo; remover a lógica antiga de `valor_fixo`.
5. **Membro principal x responsável**: AP1 tem Everton + Alexandre. O **membro principal** paga o restante (parcela + fixas não atribuídas); um membro marcado como responsável por uma categoria recebe o QR dessa categoria. É preciso deixar explícito quem é o principal de cada cota.

---

## 7. Passos de implementação (Solução A)

1. **Banco**: adicionar `valor_fixo` em `categorias`; criar tabela `responsabilidades`; adicionar `membro_id` em `cobrancas`; remover a configuração antiga de fundo do rateio e da cota (migração).
2. **Telas**: ao criar/editar categoria, campo **valor fixo** (opcional) e opção de **responsável** (membro); na cota/membro, marcação do **membro principal** e associação `membro → categoria → valor`.
3. **Geração de QR** (`fechamento_despesas`): QR por membro responsável + QR da cota (membro principal) para o restante.
4. **Fechamento de pagamentos** (`fechamento_pagamento`): reconhecer o pagamento das categorias fixas/atribuídas (crédito do responsável) no saldo da cota.
5. **Migração dos dados**: criar categoria "fundo" (valor_fixo 100) e atribuí-la ao Alexandre; remover `valor_fixo` dos membros.
6. **Limpeza e teste**: limpar `fechamentos_cota` e `creditos_cota`; recalcular em ordem cronológica; validar contra o painel financeiro.

---

## 8. Fora de escopo (não alterar)

- A regra "mês M = créditos em M+1" está **correta** e deve ser mantida (pagamento do dia 1 refere-se ao mês anterior).
