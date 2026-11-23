"""dados por usuário (fase 9, etapa 3)

Cada treino, sensação, conversa, plano, estado de sincronização e dia de carga passa a ter dono (user_id).
Os dados que já existem vão para a primeira conta do banco; sem conta nenhuma, cria-se uma conta "dono"
provisória, sem senha. FC máxima, FC de repouso e fuso do .env passam para essa conta.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-23
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

import treino.db.models

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

EMAIL_PROVISORIO = "dono@pacelab.local"
COM_ID = ("activities", "sensations", "conversations", "training_plans")


def _dono(conn) -> int | None:
    """Id da conta que recebe os dados existentes (None se o banco está vazio)."""
    tem_dados = any(
        conn.execute(sa.text(f"SELECT 1 FROM {t} LIMIT 1")).first() for t in (*COM_ID, "sync_state", "daily_load")
    )
    dono = conn.execute(sa.text("SELECT min(id) FROM users")).scalar()
    if dono is None and tem_dados:
        criado = datetime.now(UTC)
        if conn.dialect.name == "sqlite":
            criado = criado.replace(tzinfo=None)  # como o UTCDateTime grava no SQLite
        conn.execute(
            sa.text("INSERT INTO users (email, created_utc, timezone) VALUES (:e, :c, 'America/Sao_Paulo')"),
            {"e": EMAIL_PROVISORIO, "c": criado},
        )
        dono = conn.execute(sa.text("SELECT min(id) FROM users")).scalar()
    return dono


def upgrade() -> None:
    conn = op.get_bind()

    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("fc_max", sa.Integer(), nullable=True))
        b.add_column(sa.Column("fc_repouso", sa.Integer(), nullable=True))
        b.add_column(sa.Column("timezone", sa.String(length=50), nullable=False, server_default="America/Sao_Paulo"))

    dono = _dono(conn)
    if dono is not None:
        from treino.config import get_settings

        st = get_settings()
        conn.execute(
            sa.text(
                "UPDATE users SET fc_max = coalesce(fc_max, :fm), fc_repouso = coalesce(fc_repouso, :fr), "
                "timezone = :tz WHERE id = :id"
            ),
            {"fm": st.fc_max, "fr": st.fc_repouso, "tz": st.timezone, "id": dono},
        )

    # Tabelas com id próprio: coluna nova, preenchida com o dono, depois obrigatória com chave estrangeira.
    for tabela in COM_ID:
        with op.batch_alter_table(tabela) as b:
            b.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        if dono is not None:
            conn.execute(sa.text(f"UPDATE {tabela} SET user_id = :d"), {"d": dono})
        with op.batch_alter_table(tabela) as b:
            b.alter_column("user_id", existing_type=sa.Integer(), nullable=False)
            b.create_index(f"ix_{tabela}_user_id", ["user_id"], unique=False)
            b.create_foreign_key(f"fk_{tabela}_user_id", "users", ["user_id"], ["id"], ondelete="CASCADE")
            if tabela == "activities":
                b.drop_constraint("uq_activity_source", type_="unique")
                b.create_unique_constraint("uq_activity_source", ["user_id", "source", "source_id"])

    # Tabelas com chave pelo conteúdo: recriadas com o usuário na chave primária, copiando as linhas.
    op.create_table(
        "sync_state_novo",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("last_success_utc", treino.db.models.UTCDateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_utc", treino.db.models.UTCDateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_result", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "source"),
    )
    op.create_table(
        "daily_load_novo",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("trimp", sa.Float(), nullable=False),
        sa.Column("fitness", sa.Float(), nullable=False),
        sa.Column("fatigue", sa.Float(), nullable=False),
        sa.Column("form", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "day"),
    )
    if dono is not None:
        conn.execute(
            sa.text(
                "INSERT INTO sync_state_novo (user_id, source, last_success_utc, last_attempt_utc, last_error, "
                "last_result) SELECT :d, source, last_success_utc, last_attempt_utc, last_error, last_result "
                "FROM sync_state"
            ),
            {"d": dono},
        )
        conn.execute(
            sa.text(
                "INSERT INTO daily_load_novo (user_id, day, trimp, fitness, fatigue, form) "
                "SELECT :d, day, trimp, fitness, fatigue, form FROM daily_load"
            ),
            {"d": dono},
        )
    op.drop_table("sync_state")
    op.drop_table("daily_load")
    op.rename_table("sync_state_novo", "sync_state")
    op.rename_table("daily_load_novo", "daily_load")


def downgrade() -> None:
    """Volta a um dono só: mantém apenas os dados da primeira conta."""
    conn = op.get_bind()
    dono = conn.execute(sa.text("SELECT min(id) FROM users")).scalar()
    for tabela in ("sync_state", "daily_load", *COM_ID):
        conn.execute(sa.text(f"DELETE FROM {tabela} WHERE user_id <> :d"), {"d": dono or -1})

    op.create_table(
        "sync_state_velho",
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("last_success_utc", treino.db.models.UTCDateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_utc", treino.db.models.UTCDateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_result", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("source"),
    )
    op.create_table(
        "daily_load_velho",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("trimp", sa.Float(), nullable=False),
        sa.Column("fitness", sa.Float(), nullable=False),
        sa.Column("fatigue", sa.Float(), nullable=False),
        sa.Column("form", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("day"),
    )
    conn.execute(
        sa.text(
            "INSERT INTO sync_state_velho SELECT source, last_success_utc, last_attempt_utc, last_error, "
            "last_result FROM sync_state"
        )
    )
    conn.execute(sa.text("INSERT INTO daily_load_velho SELECT day, trimp, fitness, fatigue, form FROM daily_load"))
    op.drop_table("sync_state")
    op.drop_table("daily_load")
    op.rename_table("sync_state_velho", "sync_state")
    op.rename_table("daily_load_velho", "daily_load")

    for tabela in reversed(COM_ID):
        with op.batch_alter_table(tabela) as b:
            if tabela == "activities":
                b.drop_constraint("uq_activity_source", type_="unique")
                b.create_unique_constraint("uq_activity_source", ["source", "source_id"])
            b.drop_constraint(f"fk_{tabela}_user_id", type_="foreignkey")
            b.drop_index(f"ix_{tabela}_user_id")
            b.drop_column("user_id")

    with op.batch_alter_table("users") as b:
        b.drop_column("timezone")
        b.drop_column("fc_repouso")
        b.drop_column("fc_max")
