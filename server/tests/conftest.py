"""Fixtures compartilhadas pelos testes (dados sintéticos)."""

import gzip
import zipfile

import pytest

from treino import services
from treino.config import get_settings
from treino.db import init_db, session_scope
from treino.db.session import get_engine
from treino.ingest.strava_export import import_strava_export

from test_basico import make_csv, make_gpx


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Banco temporário com duas corridas sintéticas (a segunda é duplicata da primeira) e uma caminhada."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path.as_posix()}/ia.db")
    monkeypatch.setenv("FC_MAX", "190")
    monkeypatch.setenv("API_TOKEN", "teste")
    get_settings.cache_clear()
    get_engine.cache_clear()
    init_db()
    zpath = tmp_path / "export.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr(
            "activities.csv",
            make_csv(
                [
                    '10,"20 de out. de 2026, 10:00:00",Corrida A,Corrida,700,"2,00",160,activities/10.gpx.gz,700.0,699.0,2000.0,86.0,150.0',
                    '11,"20 de out. de 2026, 10:03:00",Corrida A copia,Corrida,700,"2,00",160,,700.0,699.0,2000.0,86.0,150.0',
                    '12,"18 de out. de 2026, 10:00:00",Passeio,Caminhada,600,"0,5",120,,600.0,600.0,500.0,110.0,100.0',
                ]
            ),
        )
        z.writestr("activities/10.gpx.gz", gzip.compress(make_gpx(n=700)))
    with session_scope() as s:
        import_strava_export(s, zpath)
        services.recompute(s, get_settings())
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()
