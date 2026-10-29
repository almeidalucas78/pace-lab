from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect, select

from treino import services
from treino.config import Settings
from treino.db import init_db, session_scope
from treino.db.models import Activity, Base, SyncState
from treino.db.session import get_engine
from treino.ingest.hc_client import HCUnavailable
from treino.ingest.health_connect import normalize_sport, parse_payload

T0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
LOCAL = timezone(timedelta(hours=-3))


def iso(dt, local=False):
    return (dt.astimezone(LOCAL) if local else dt).isoformat().replace("+00:00", "Z")


def make_payload(minutes=20, hr=150, dist_every_s=60, speed=3.0, aggregated=False, record_id="hc-1",
                 type_="EXERCISE_TYPE_RUNNING", start=T0):
    """Corrida sintética no formato documentado do HC Webhook."""
    end = start + timedelta(minutes=minutes)
    if aggregated:
        hrs = [{"time": iso(start + timedelta(minutes=m)), "avg": hr, "min": hr - 5, "max": hr + 5, "bpm": hr}
               for m in range(minutes)]
    else:
        hrs = [{"bpm": hr, "time": iso(start + timedelta(seconds=s))} for s in range(minutes * 60)]
    dists = [{"meters": speed * dist_every_s, "start_time": iso(start + timedelta(seconds=s)),
              "end_time": iso(start + timedelta(seconds=s + dist_every_s))}
             for s in range(0, minutes * 60, dist_every_s)]
    return {
        "timestamp": iso(end), "app_version": "teste",
        "exercise": [{"type": type_, "start_time": iso(start, local=True), "end_time": iso(end, local=True),
                      "duration_seconds": minutes * 60, "distance_meters": speed * minutes * 60,
                      "avg_cadence_spm": 170, "steps": 3400,
                      "metadata": {"id": record_id, "data_origin": "com.sec.android.app.shealth"}}],
        "heart_rate": hrs, "distance": dists,
    }


def test_tipo_de_exercicio():
    assert normalize_sport("EXERCISE_TYPE_RUNNING") == "run"
    assert normalize_sport("running_treadmill") == "run"
    assert normalize_sport("WALKING") == "walk"
    assert normalize_sport("YOGA") == "other"


def test_sessao_com_amostras_e_distancia_curta():
    p = parse_payload(make_payload())
    (s,) = p.sessions
    assert s.source_id == "hc-1" and s.sport == "run"
    assert s.start_utc == T0                      # horário local com deslocamento vira UTC
    assert s.distance_m == 3600 and s.avg_hr == 150
    assert s.notes["distancia_por_ponto"] is True and s.notes["fc_resolucao"] == "amostras"
    mid = next(pt for pt in s.points if pt.time == T0 + timedelta(seconds=90))
    assert mid.dist == pytest.approx(270)         # interpolado entre os registros de distância


def test_fc_agregada_e_distancia_longa_nao_inventa_parciais():
    p = parse_payload(make_payload(aggregated=True, dist_every_s=1200))
    (s,) = p.sessions
    assert s.notes["fc_resolucao"] == "agregada"
    assert s.notes["distancia_por_ponto"] is False and "aviso_distancia" in s.notes
    assert all(pt.dist is None for pt in s.points) and len(s.points) == 20


class FakeClient:
    def __init__(self, payload):
        self.payload, self.calls = payload, []

    def read(self, start, end):
        self.calls.append((start, end))
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


@pytest.fixture
def engine(tmp_path):
    get_engine.cache_clear()
    eng = get_engine(f"sqlite:///{tmp_path}/hc.db")
    init_db(eng)
    yield eng
    get_engine.cache_clear()


SETTINGS = Settings(fc_max=190, timezone="America/Sao_Paulo", hc_url="http://celular:8787", sync_margem_h=48)


def test_sincronizacao_idempotente_com_parciais(engine):
    now = T0 + timedelta(hours=2)
    client = FakeClient(make_payload())
    with session_scope(engine) as s:
        rep = services.sync_health_connect(s, SETTINGS, client, now=now)
    assert rep["status"] == "ok" and rep["novas"] == 1 and len(rep["novos"]) == 1
    assert client.calls[0][0] == now - timedelta(days=30)   # primeira leitura

    later = now + timedelta(hours=1)
    with session_scope(engine) as s:
        rep = services.sync_health_connect(s, SETTINGS, client, now=later)
        acts = s.scalars(select(Activity)).all()
        assert rep["novas"] == 0 and rep["atualizadas"] == 1 and rep["novos"] == []
        assert client.calls[1][0] == now - timedelta(hours=48)  # desde o último sucesso menos a margem
        (a,) = acts
        assert a.source == "health_connect" and [sp.km for sp in a.splits] == [1, 2, 3, 4]
        assert a.trimp == pytest.approx(20 * 3, abs=0.5)   # 150/190 = 79% -> z3 (peso 3) por 20 min
        assert s.get(SyncState, "health_connect").last_success_utc == later


def test_strava_prevalece_na_duplicata(engine):
    with session_scope(engine) as s:
        # mesmo treino no Strava, registrado 2 min depois do início no relógio
        s.add(Activity(source="strava", source_id="99", sport="run", start_utc=T0 + timedelta(minutes=2),
                       distance_m=3600, moving_s=1200))
    with session_scope(engine) as s:
        rep = services.sync_health_connect(s, SETTINGS, FakeClient(make_payload()), now=T0 + timedelta(hours=2))
        assert rep["novas"] == 1 and rep["novas_duplicadas"] == 1 and rep["novos"] == []
        hc = s.scalar(select(Activity).where(Activity.source == "health_connect"))
        strava = s.scalar(select(Activity).where(Activity.source == "strava"))
        assert hc.possible_duplicate_of == strava.id and strava.possible_duplicate_of is None


def test_registro_apagado_no_health_connect(engine):
    with session_scope(engine) as s:
        services.sync_health_connect(s, SETTINGS, FakeClient(make_payload()), now=T0 + timedelta(hours=2))
    with session_scope(engine) as s:
        rep = services.sync_health_connect(
            s, SETTINGS, FakeClient({"deleted": [{"type": "exercise", "id": "hc-1"}]}), now=T0 + timedelta(hours=3))
        assert rep["apagadas"] == 1 and s.scalars(select(Activity)).all() == []


def test_celular_indisponivel_nao_avanca_a_janela(engine):
    with session_scope(engine) as s:
        rep = services.sync_health_connect(s, SETTINGS, FakeClient(HCUnavailable("sem rede")), now=T0)
    assert rep["status"] == "indisponivel"
    with session_scope(engine) as s:
        st = s.get(SyncState, "health_connect")
        assert st.last_success_utc is None and st.last_error == "sem rede" and st.last_attempt_utc == T0


def test_migracao_de_banco_da_fase_1(tmp_path):
    url = f"sqlite:///{tmp_path}/antigo.db"
    old = create_engine(url)
    Base.metadata.tables["activities"].create(old)   # banco criado com create_all, sem Alembic
    for t in ("samples", "splits", "daily_load"):
        Base.metadata.tables[t].create(old)
    with old.begin() as c:
        c.exec_driver_sql("INSERT INTO activities (source, source_id, sport, start_utc, file_status, hr_quality) "
                          "VALUES ('strava', '1', 'run', '2026-01-01 10:00:00', 'ok', 'ok')")
    old.dispose()
    get_engine.cache_clear()
    eng = get_engine(url)
    init_db(eng)
    init_db(eng)   # rodar de novo não faz nada
    names = inspect(eng).get_table_names()
    assert "alembic_version" in names and "sync_state" in names
    with session_scope(eng) as s:
        assert len(s.scalars(select(Activity)).all()) == 1
    get_engine.cache_clear()
