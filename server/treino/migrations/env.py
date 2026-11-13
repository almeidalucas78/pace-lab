"""Ambiente do Alembic. Usa a conexão passada por init_db ou, na linha de comando, o DATABASE_URL do .env."""

from alembic import context
from sqlalchemy import create_engine

from treino.config import get_settings
from treino.db.models import Base


def _run(connection) -> None:
    # render_as_batch: o SQLite não altera colunas no lugar; o Alembic recria a tabela.
    context.configure(
        connection=connection, target_metadata=Base.metadata, render_as_batch=connection.dialect.name == "sqlite"
    )
    with context.begin_transaction():
        context.run_migrations()


connection = context.config.attributes.get("connection")
if connection is not None:
    _run(connection)
else:
    with create_engine(get_settings().sqlite_url).connect() as conn:
        _run(conn)
        conn.commit()
