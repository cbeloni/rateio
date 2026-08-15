"""Adiciona membros.principal (membro principal da cota)."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _coluna_existe(conn, tabela, coluna):
    return (
        conn.execute(text(f"SHOW COLUMNS FROM `{tabela}` LIKE :c"), {"c": coluna}).first()
        is not None
    )


def upgrade():
    conn = op.get_bind()
    if not _coluna_existe(conn, "membros", "principal"):
        op.add_column(
            "membros",
            sa.Column("principal", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )


def downgrade():
    conn = op.get_bind()
    if _coluna_existe(conn, "membros", "principal"):
        op.drop_column("membros", "principal")
