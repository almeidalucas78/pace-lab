"""Banco dos testes: SQLite (padrão, rápido) ou Postgres, quando TESTE_POSTGRES_URL estiver definida (ADR 0015).

Postgres local: `docker compose -f infra/teste/docker-compose.yml up -d` e
`TESTE_POSTGRES_URL=postgresql+psycopg://teste:teste@127.0.0.1:55432/teste` (no CI, um serviço do GitHub Actions).
Cada teste recebe o banco zerado (o esquema `public` é apagado e recriado).
"""

from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine

POSTGRES = os.environ.get("TESTE_POSTGRES_URL", "")


def url_banco(tmp_path: Path, nome: str = "t.db") -> str:
    if not POSTGRES:
        return f"sqlite:///{tmp_path.as_posix()}/{nome}"
    eng = create_engine(POSTGRES)
    with eng.begin() as c:
        # Conexões que sobraram de testes anteriores seguram o esquema; derruba antes de apagar.
        c.exec_driver_sql(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = current_database() AND pid <> pg_backend_pid()"
        )
        c.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
        c.exec_driver_sql("CREATE SCHEMA public")
    eng.dispose()
    return POSTGRES
