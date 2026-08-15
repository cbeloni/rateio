"""Adiciona rateios.valor_inicial_caixa (saldo inicial do caixa)."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def _coluna_existe(conn, tabela, coluna):
    return (
        conn.execute(text(f"SHOW COLUMNS FROM `{tabela}` LIKE :c"), {"c": coluna}).first()
        is not None
    )


def upgrade():
    conn = op.get_bind()
    if not _coluna_existe(conn, "rateios", "valor_inicial_caixa"):
        op.add_column(
            "rateios",
            sa.Column("valor_inicial_caixa", sa.DECIMAL(10, 2), nullable=False, server_default=sa.text("0.00")),
        )


def downgrade():
    conn = op.get_bind()
    if _coluna_existe(conn, "rateios", "valor_inicial_caixa"):
        op.drop_column("rateios", "valor_inicial_caixa")
