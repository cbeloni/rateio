"""Cria o registro de tentativas de login."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _tabela_existe(conn, tabela):
    return (
        conn.execute(text("SHOW TABLES LIKE :t"), {"t": tabela}).first()
        is not None
    )


def upgrade():
    conn = op.get_bind()
    if _tabela_existe(conn, "login"):
        return

    op.create_table(
        "login",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("sucesso", sa.Boolean(), nullable=False),
        sa.Column("data_hora", sa.DateTime(), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("ip_encaminhado", sa.String(length=1024), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("idioma", sa.String(length=255), nullable=True),
        sa.Column("rota", sa.String(length=255), nullable=False),
        sa.Column("motivo", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        mysql_engine="InnoDB",
    )
    op.create_index("ix_login_usuario_id", "login", ["usuario_id"])
    op.create_index("ix_login_data_hora", "login", ["data_hora"])


def downgrade():
    conn = op.get_bind()
    if _tabela_existe(conn, "login"):
        op.drop_table("login")
