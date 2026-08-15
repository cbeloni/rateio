"""Adiciona membros.receber_mensagens (opt-out de mensagens)."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _coluna_existe(conn, tabela, coluna):
    return (
        conn.execute(text(f"SHOW COLUMNS FROM `{tabela}` LIKE :c"), {"c": coluna}).first()
        is not None
    )


def upgrade():
    conn = op.get_bind()
    if not _coluna_existe(conn, "membros", "receber_mensagens"):
        op.add_column(
            "membros",
            sa.Column("receber_mensagens", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        )


def downgrade():
    conn = op.get_bind()
    if _coluna_existe(conn, "membros", "receber_mensagens"):
        op.drop_column("membros", "receber_mensagens")
