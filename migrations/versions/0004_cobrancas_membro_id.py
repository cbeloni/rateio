"""Adiciona cobrancas.membro_id (QR Code por membro)."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _coluna_existe(conn, tabela, coluna):
    return (
        conn.execute(text(f"SHOW COLUMNS FROM `{tabela}` LIKE :c"), {"c": coluna}).first()
        is not None
    )


def upgrade():
    conn = op.get_bind()
    if not _coluna_existe(conn, "cobrancas", "membro_id"):
        op.add_column(
            "cobrancas",
            sa.Column("membro_id", sa.Integer(), nullable=True),
        )


def downgrade():
    conn = op.get_bind()
    if _coluna_existe(conn, "cobrancas", "membro_id"):
        op.drop_column("cobrancas", "membro_id")
