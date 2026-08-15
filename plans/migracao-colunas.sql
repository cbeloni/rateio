-- =============================================================================
-- Migração manual de colunas ausentes (produção)
-- =============================================================================
-- Executar UMA VEZ no banco de produção quando o deploy gerar:
--   "Unknown column 'rateios.valor_inicial_caixa' in 'field list'"
--
--   mysql -h <host> -u <user> -p <database> < plans/migracao-colunas.sql
--
-- OBS: o app também aplica estas colunas automaticamente na inicialização
-- (repository/base.py -> criar_tabelas_rateio), então este script é opcional,
-- servindo para corrigir o banco antes de um novo deploy.
-- =============================================================================

-- 1) Coluna que falta no rateio (erro atual em produção).
ALTER TABLE rateios ADD COLUMN valor_inicial_caixa DECIMAL(10,2) NOT NULL DEFAULT 0.00;

-- 2) Demais colunas que podem faltar em bancos antigos (executar se necessário):
-- ALTER TABLE membros ADD COLUMN receber_mensagens BOOLEAN NOT NULL DEFAULT TRUE;
-- ALTER TABLE membros ADD COLUMN principal BOOLEAN NOT NULL DEFAULT FALSE;
-- ALTER TABLE cobrancas ADD COLUMN membro_id INT NULL;
-- ALTER TABLE categorias ADD COLUMN valor_fixo DECIMAL(10,2) NULL;
