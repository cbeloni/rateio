"""Remove membros.valor_fixo (valor fixo agora fica na categoria)."""
from alembic import op
from sqlalchemy import text

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def _coluna_existe(conn, tabela, coluna):
    return (
        conn.execute(text(f"SHOW COLUMNS FROM `{tabela}` LIKE :c"), {"c": coluna}).first()
        is not None
    )


def upgrade():
    conn = op.get_bind()
    if _coluna_existe(conn, "membros", "valor_fixo"):
        op.drop_column("membros", "valor_fixo")


def downgrade():
    import sqlalchemy as sa

    conn = op.get_bind()
    if not _coluna_existe(conn, "membros", "valor_fixo"):
        op.add_column(
            "membros",
            sa.Column("valor_fixo", sa.DECIMAL(10, 2), nullable=True),
        )
