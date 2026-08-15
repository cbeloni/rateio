# Valores de referência para conferência (Painel Financeiro)

Referência usada para validar os fechamentos do rateio "Aruja" (id=1).

## Despesas

| Mês | ENEL | SABESP | FAXINA | OUTROS | TOTAL | PARCELA |
|-----|------|--------|--------|--------|-------|---------|
| Janeiro | 48,65 | 76,64 | 308,00 | 29,99 | 463,28 | 115,82 |
| Fevereiro | 48,85 | 81,24 | 308,00 | 0,00 | 438,09 | 109,52 |
| Março | 48,64 | 83,07 | 308,00 | 0,00 | 439,71 | 109,93 |
| Abril | 48,43 | 83,00 | 308,00 | 257,05 | 696,48 | 174,12 |
| Maio | 49,34 | 83,22 | 308,00 | 0,00 | 440,56 | 110,14 |
| Junho | 49,18 | 83,08 | 308,00 | 0,00 | 440,26 | 110,07 |
| Julho | 50,34 | 81,24 | 0,00 | 0,00 | 131,58 | 32,90 |
| Agosto | 0,00 | 0,00 | 0,00 | 28,77 | 28,77 | 7,19 |

## Pagamentos

| Mês | AP1 | AP2 | AP3 | AP4 | TOTAL |
|-----|-----|-----|-----|-----|-------|
| Janeiro | 215,82 | 215,82 | 215,82 | 215,82 | 863,28 |
| Fevereiro | 209,52 | 209,52 | 209,52 | 209,52 | 838,08 |
| Março | 209,93 | 209,93 | 209,93 | 209,93 | 839,72 |
| Abril | 274,12 | 274,12 | 274,12 | 274,12 | 1096,48 |
| Maio | 210,14 | 210,14 | 210,14 | 210,14 | 840,56 |
| Junho | 210,07 | 210,07 | 210,07 | 210,07 | 840,28 |
| Julho | 100,00 | 132,90 | 132,90 | 132,90 | 498,70 |
| Agosto | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |

## Fundo / Caixa

| Mês | AP1 | AP2 | AP3 | AP4 | TOTAL |
|-----|-----|-----|-----|-----|-------|
| Janeiro | 100,00 | 100,00 | 100,00 | 100,00 | 400,00 |
| Fevereiro | 100,00 | 100,00 | 100,00 | 100,00 | 400,00 |
| Março | 100,00 | 100,00 | 100,00 | 100,00 | 400,00 |
| Abril | 100,00 | 100,00 | 100,00 | 100,00 | 400,00 |
| Maio | 100,00 | 100,00 | 100,00 | 100,00 | 400,00 |
| Junho | 100,00 | 100,00 | 100,00 | 100,00 | 400,00 |
| Julho | 67,10 | 100,00 | 100,00 | 100,00 | 367,10 |
| Agosto | 0,00 | 0,00 | 0,00 | 0,00 | 0,00 |

## Transferências de saldo aplicadas (atribuição de pagamentos)

| Cota | Origem | Destino | Valor | Motivo |
|------|--------|---------|-------|--------|
| AP1 | Fevereiro | Janeiro | 115,82 | Parcela de Janeiro paga em atraso (03/Mar) |
| AP2 | Janeiro | Fevereiro | 209,52 | Parcela de Fevereiro paga adiantada (28/Fev) |
| AP2 | Junho | Julho | 132,90 | Pagamento de Julho adiantado (31/Jul) |

## Regras

- Fechamento do mês M usa os créditos do extrato do mês M+1.
- `pagamentos` = total do extrato + créditos recebidos.
- `pagamentos_liquido` (aba Pagamentos) = pagamentos − valor transferido.
- `fundo` = excedente sobre a parcela, limitado ao fundo da cota (100,00).
- `saldo` = acumulado; deve fechar em 0,00 para meses quitados.
- Atribuição de pagamento fora do mês esperado é feita exclusivamente pela função "Mover saldo" (qualquer mês com fechamento).
