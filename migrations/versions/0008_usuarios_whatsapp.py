"""Adiciona usuarios.whatsapp_session_id e usuarios.whatsapp_conectado (multi-sessão WhatsApp)."""
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
    if not _coluna_existe(conn, "usuarios", "whatsapp_session_id"):
        op.add_column(
            "usuarios",
            sa.Column("whatsapp_session_id", sa.String(64), nullable=True),
        )
    if not _coluna_existe(conn, "usuarios", "whatsapp_conectado"):
        op.add_column(
            "usuarios",
            sa.Column(
                "whatsapp_conectado",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            ),
        )


def downgrade():
    conn = op.get_bind()
    if _coluna_existe(conn, "usuarios", "whatsapp_conectado"):
        op.drop_column("usuarios", "whatsapp_conectado")
    if _coluna_existe(conn, "usuarios", "whatsapp_session_id"):
        op.drop_column("usuarios", "whatsapp_session_id")
