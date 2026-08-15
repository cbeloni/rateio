"""Adiciona categorias.valor_fixo (categoria de valor fixo mensal)."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _coluna_existe(conn, tabela, coluna):
    return (
        conn.execute(text(f"SHOW COLUMNS FROM `{tabela}` LIKE :c"), {"c": coluna}).first()
        is not None
    )


def upgrade():
    conn = op.get_bind()
    if not _coluna_existe(conn, "categorias", "valor_fixo"):
        op.add_column(
            "categorias",
            sa.Column("valor_fixo", sa.DECIMAL(10, 2), nullable=True),
        )


def downgrade():
    conn = op.get_bind()
    if _coluna_existe(conn, "categorias", "valor_fixo"):
        op.drop_column("categorias", "valor_fixo")
