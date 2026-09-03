"""Adiciona o perfil do membro por rateio."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _coluna_existe(conn, tabela, coluna):
    return (
        conn.execute(text(f"SHOW COLUMNS FROM `{tabela}` LIKE :c"), {"c": coluna}).first()
        is not None
    )


def upgrade():
    conn = op.get_bind()
    if not _coluna_existe(conn, "membros", "perfil"):
        op.add_column(
            "membros",
            sa.Column(
                "perfil",
                sa.String(length=20),
                nullable=False,
                server_default="membro",
            ),
        )
        op.execute(
            sa.text(
                """
                UPDATE membros m
                INNER JOIN cotas c ON c.id = m.cota_id
                INNER JOIN rateios r ON r.id = c.rateio_id
                SET m.perfil = 'organizador'
                WHERE m.usuario_id = r.organizador_id
                """
            )
        )


def downgrade():
    conn = op.get_bind()
    if _coluna_existe(conn, "membros", "perfil"):
        op.drop_column("membros", "perfil")
