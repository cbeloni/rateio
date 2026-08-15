-- =============================================================================
-- Limpar fechamentos e transferências de saldo
-- =============================================================================
-- Uso: executar antes de refazer os fechamentos e as transferências de saldo.
--   mysql -h <host> -u <user> -p <database> < plans/limpar-fechamentos-transferencias.sql
--
-- Este script remove:
--   1. fechamentos_cota  -> todos os fechamentos mensais por cota
--   2. creditos_cota     -> todas as transferências de saldo (mover saldo)
--
-- Depois de executar, refaça na ordem:
--   a) fechar as despesas de cada mês (service/fechamento_despesas.py);
--   b) aplicar as transferências de saldo (mover saldo), se houver;
--   c) recalcular os fechamentos (recalcular_fechamentos).
--
-- Observação: se quiser uma limpeza completa (recomeçar do zero), descomente as
-- linhas de `despesas` e `cobrancas` abaixo — elas também são recriadas ao
-- refazer os fechamentos e ao gerar os QR Codes.
-- =============================================================================

-- 1) Remove todos os fechamentos mensais por cota.
DELETE FROM fechamentos_cota;

-- 2) Remove todas as transferências de saldo (mover saldo).
DELETE FROM creditos_cota;

-- Opcional: limpar também as despesas e as cobranças (QR Codes).
-- DELETE FROM despesas;
-- DELETE FROM cobrancas;
