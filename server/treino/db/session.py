from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..config import get_settings


@lru_cache
def get_engine(url: str | None = None) -> Engine:
    url = url or get_settings().sqlite_url
    if url.startswith("sqlite:///"):
        db_path = Path(url.removeprefix("sqlite:///"))
        if str(db_path) != ":memory:":
            db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, future=True)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _pragmas(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

    return engine


MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
BASELINE_REVISION = "0001"  # esquema da fase 1, quando o banco era criado com create_all


def init_db(engine: Engine | None = None) -> None:
    """Cria ou atualiza o banco aplicando as migrações do Alembic (seguro rodar de novo)."""
    from alembic import command
    from alembic.config import Config

    engine = engine or get_engine()
    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    with engine.connect() as conn:
        if conn.dialect.name == "sqlite":
            # Recriar tabela (batch do Alembic) com FK ligada apagaria amostras em cascata.
            conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        cfg.attributes["connection"] = conn
        insp = inspect(conn)
        if insp.has_table("activities") and not insp.has_table("alembic_version"):
            command.stamp(cfg, BASELINE_REVISION)  # banco da fase 1: já tem o esquema inicial
        command.upgrade(cfg, "head")
        conn.commit()
        if conn.dialect.name == "sqlite":
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")


@contextmanager
def session_scope(engine: Engine | None = None):
    factory = sessionmaker(bind=engine or get_engine(), expire_on_commit=False)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
