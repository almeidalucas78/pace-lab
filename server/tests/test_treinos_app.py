"""Treinos enviados pelo app Android (ADR 0013), com dados sintéticos no formato do Samsung Health Data SDK."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from treino.api import app as app_mod
from treino.api.app import app
from treino.db import session_scope
from treino.db.models import Activity, SyncState
from treino.ingest.treinos_app import converter, esporte, juntar_pontos

H = {"Authorization": "Bearer teste"}
INICIO = datetime(2026, 11, 3, 21, 18, 0, tzinfo=UTC)  # 18:18 em Brasília


def corrida(id_="sh-1", segundos=1000, vel=3.0, fc=150, inicio=INICIO, com_gps=True, desvio_gps_ms=0):
    """Corrida sintética: 1 registro e 1 ponto de GPS por segundo, rumo ao norte a `vel` m/s.
    `desvio_gps_ms`: o relógio real grava o GPS uns 100 ms depois dos sensores."""
    ms0 = int(inicio.timestamp() * 1000)
    dlat = vel / 111_320
    return {
        "id": id_,
        "tipo": "RUNNING",
        "inicio": inicio.isoformat(),
        "fim": (inicio + timedelta(seconds=segundos)).isoformat(),
        "duracao_s": segundos,
        "distancia_m": vel * segundos,
        "calorias": 250,
        "fc_media": fc,
        "fc_max": fc + 10,
        "cadencia_media": 170,
        "ganho_elevacao_m": 12,
        "vo2max": 47.5,
        "registros": [
            {"t": ms0 + i * 1000, "fc": fc if i != 500 else 0, "vel": vel, "cad": 170} for i in range(segundos)
        ],
        "percurso": [
            {"t": ms0 + i * 1000 + desvio_gps_ms, "lat": -23.5 + i * dlat, "lon": -46.6, "alt": 750 + i / 100}
            for i in range(segundos)
        ]
        if com_gps
        else [],
    }


def lote(*treinos, apagados=()):
    return {"fonte": "samsung_health", "treinos": list(treinos), "apagados": list(apagados)}


def test_tipos_e_juncao_dos_pontos():
    assert esporte("RUNNING") == "run" and esporte("treadmill") == "run" and esporte("HIKING") == "walk"
    assert esporte("BIKING") == "ride" and esporte("YOGA") == "other"
    pontos = juntar_pontos(
        [{"t": 2000, "fc": 150, "vel": 3}, {"t": 1000, "fc": 0, "vel": 3}],
        [{"t": 1000, "lat": -23.5, "lon": -46.6}, {"t": 3000, "lat": -23.4, "lon": -46.6}],
    )
    assert [p.time.second for p in pontos] == [1, 2, 3]
    assert pontos[0].hr is None and pontos[0].lat == -23.5  # FC 0 do relógio vira "sem leitura"
    assert pontos[1].hr == 150 and pontos[1].lat is None


def test_gps_fora_de_sincronia_com_os_sensores(db):
    """Galaxy Watch: GPS, FC e velocidade em registros e horários próprios. Próximos (< 0,5 s) viram um ponto;
    mais afastados ficam intercalados e as parciais ainda precisam sair certas (antes davam 1:16/km)."""
    pontos = juntar_pontos(
        [{"t": 1000, "fc": 150}, {"t": 1050, "vel": 3, "cad": 160}, {"t": 2000, "fc": 151}],
        [{"t": 1100, "lat": -23.5, "lon": -46.6}, {"t": 2100, "lat": -23.4, "lon": -46.6}],
    )
    assert len(pontos) == 2 and pontos[0].hr == 150 and pontos[0].speed == 3 and pontos[0].lat == -23.5
    assert pontos[1].hr == 151 and pontos[1].lat == -23.4
    with TestClient(app) as c:
        tid = c.post("/api/saude/treinos", json=lote(corrida(desvio_gps_ms=500)), headers=H).json()["novos_ids"][0]
        d = c.get(f"/api/activities/{tid}", headers=H).json()
    assert all(p["ritmo"] in ("5:32/km", "5:33/km", "5:34/km") for p in d["parciais"][:3])
    assert all(p["fc_media"] == 150 for p in d["parciais"][:3])


def test_converter_resumo():
    from treino.api.app import TreinoIn

    t = converter("samsung_health", TreinoIn(**corrida(segundos=10)).model_dump())
    assert t.esporte == "run" and t.inicio == INICIO and t.extras["vo2max"] == 47.5
    assert t.extras == {"vo2max": 47.5, "pontos_gps": 10, "registros": 10} and len(t.pontos) == 10


def test_recebe_corrida_com_mapa_parciais_e_carga(db, monkeypatch):
    avisos = []
    monkeypatch.setattr(app_mod, "notify", lambda *a, **k: avisos.append(a))
    with TestClient(app) as c:
        r = c.post("/api/saude/treinos", json=lote(corrida()), headers=H)
        assert r.status_code == 200, r.text
        rep = r.json()
        assert rep["novos"] == 1 and rep["novos_duplicados"] == 0 and len(rep["novos_ids"]) == 1
        tid = rep["novos_ids"][0]
        d = c.get(f"/api/activities/{tid}", headers=H).json()
        assert d["esporte"] == "run" and d["distancia_km"] == 3.0 and d["ritmo"] == "5:33/km"
        assert [p["km"] for p in d["parciais"]] == [1, 2, 3]
        assert d["carga"] and d["zonas_fc_min"]
        amostras = c.get(f"/api/activities/{tid}/samples?every_s=5", headers=H).json()
        assert sum(1 for a in amostras if a["lat"]) == len(amostras) == 200
    assert avisos and "Corrida" in avisos[0][1]
    with session_scope() as s:
        st = s.get(SyncState, "samsung_health")
        assert st.last_success_utc and st.last_result["novos"] == 1


def test_reenvio_e_idempotente_e_apagado_remove(db):
    with TestClient(app) as c:
        assert c.post("/api/saude/treinos", json=lote(corrida()), headers=H).json()["novos"] == 1
        r = c.post("/api/saude/treinos", json=lote(corrida()), headers=H).json()
        assert r["novos"] == 0 and r["atualizados"] == 1
        r = c.post("/api/saude/treinos", json=lote(apagados=["sh-1"]), headers=H).json()
        assert r["apagados"] == 1
    with session_scope() as s:
        assert s.scalar(select(Activity).where(Activity.source == "samsung_health")) is None


def test_strava_prevalece_sobre_o_samsung_health(db):
    # a corrida de 20/10 10:00 UTC já existe no banco de teste, vinda do Strava
    with TestClient(app) as c:
        r = c.post(
            "/api/saude/treinos", json=lote(corrida(inicio=datetime(2026, 10, 20, 10, 2, tzinfo=UTC))), headers=H
        ).json()
    assert r["novos"] == 1 and r["novos_duplicados"] == 1 and r["novos_ids"] == []
    with session_scope() as s:
        sh = s.scalar(select(Activity).where(Activity.source == "samsung_health"))
        assert sh.possible_duplicate_of is not None
        assert s.get(Activity, sh.possible_duplicate_of).source == "strava"


def test_treino_sem_gps_e_validacoes(db):
    with TestClient(app) as c:
        r = c.post("/api/saude/treinos", json=lote(corrida(id_="esteira", com_gps=False)), headers=H)
        assert r.status_code == 200
        ruim = corrida(id_="x")
        ruim["fim"] = ruim["inicio"]
        assert c.post("/api/saude/treinos", json=lote(ruim), headers=H).status_code == 422
        sem_fuso = corrida(id_="y")
        sem_fuso["inicio"] = "2026-11-03T18:18:00"
        assert c.post("/api/saude/treinos", json=lote(sem_fuso), headers=H).status_code == 422
        assert c.post("/api/saude/treinos", json={**lote(), "fonte": "outra"}, headers=H).status_code == 422
        assert c.post("/api/saude/treinos", json=lote()).status_code == 401


def esteira(id_="esteira-1", segundos=1200, vel=2.8, gps_zerado=True):
    """Esteira como o Samsung Health manda: percurso com (0, 0) em todos os pontos e velocidade no registro."""
    t = corrida(id_=id_, segundos=segundos, vel=vel)
    t["percurso"] = [{"t": g["t"], "lat": 0.0, "lon": 0.0} for g in t["percurso"]] if gps_zerado else []
    return t


def test_esteira_sem_gps_tem_parciais_pela_velocidade(db):
    with TestClient(app) as c:
        tid = c.post("/api/saude/treinos", json=lote(esteira()), headers=H).json()["novos_ids"][0]
        d = c.get(f"/api/activities/{tid}", headers=H).json()
        assert [p["km"] for p in d["parciais"]] == [1, 2, 3, 4]  # 3,36 km: 3 cheios e o resto
        assert d["observacoes_dados"]["distancia_fonte"] == "velocidade"
        assert d["observacoes_dados"]["pontos_gps"] == 0
        amostras = c.get(f"/api/activities/{tid}/samples?every_s=5", headers=H).json()
        assert all(a["lat"] is None for a in amostras)  # nada de mapa no meio do oceano


def test_musculacao_com_gps_zerado_fica_sem_gps(db):
    forca = corrida(id_="forca", segundos=600, vel=0.0)
    forca["tipo"] = "WEIGHT_MACHINE"
    forca["percurso"] = [{"t": g["t"], "lat": 0.0, "lon": 0.0} for g in forca["percurso"]]
    with TestClient(app) as c:
        tid = c.post("/api/saude/treinos", json=lote(forca), headers=H).json()["novos_ids"][0]
        amostras = c.get(f"/api/activities/{tid}/samples?every_s=60", headers=H).json()
        assert amostras and all(a["lat"] is None for a in amostras)


def test_reprocessar_treinos_ja_gravados_com_gps_zerado(db):
    from treino import services
    from treino.config import get_settings
    from treino.db.models import Sample

    # simula o que ficou no banco antes da correção: amostras com lat/lon 0 e sem distância
    with TestClient(app) as c:
        tid = c.post("/api/saude/treinos", json=lote(esteira(gps_zerado=False)), headers=H).json()["novos_ids"][0]
    with session_scope() as s:
        for amostra in s.scalars(select(Sample).where(Sample.activity_id == tid)):
            amostra.lat, amostra.lon, amostra.dist_m = 0.0, 0.0, 0.0
    with session_scope() as s:
        assert services.reprocess_app_workouts(s, get_settings())["reprocessados"] == 1
    with session_scope() as s:
        a = s.get(Activity, tid)
        assert [sp.km for sp in a.splits] == [1, 2, 3, 4] and a.extra["pontos_gps"] == 0
        assert s.scalar(select(Sample).where(Sample.activity_id == tid, Sample.lat.is_not(None))) is None
