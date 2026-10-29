import gzip
import zipfile
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from treino.config import Settings
from treino.core.load import daily_series, trimp_from_zones, zones_from_samples
from treino.core.streams import process_points
from treino.db import init_db, session_scope
from treino.db.models import Activity
from treino.db.session import get_engine
from treino.ingest.files import parse_activity_file
from treino.ingest.strava_csv import parse_date, read_activities_csv
from treino.ingest.strava_export import import_strava_export
from treino import services

T0 = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
HEADER = ("ID da atividade,Data da atividade,Nome da atividade,Tipo de atividade,Tempo decorrido,Distância,"
          "Frequência cardíaca máxima,Nome do arquivo,Tempo decorrido,Tempo de movimentação,Distância,"
          "Cadência média,Frequência cardíaca média")


def make_gpx(n=600, speed=3.0, hr=150):
    """Corrida sintética: 1 ponto/s rumo ao norte, ~speed m/s."""
    dlat = speed / 111_320
    pts = "".join(
        f'<trkpt lat="{-23.5 + i * dlat:.7f}" lon="-46.6"><ele>700</ele>'
        f'<time>{(T0 + timedelta(seconds=i)).isoformat().replace("+00:00", "Z")}</time>'
        f'<extensions><gpxtpx:TrackPointExtension><gpxtpx:hr>{hr}</gpxtpx:hr></gpxtpx:TrackPointExtension></extensions></trkpt>'
        for i in range(n))
    return (f'<?xml version="1.0"?><gpx xmlns="http://www.topografix.com/GPX/1/1" '
            f'xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" creator="Samsung Health_0.2">'
            f'<trk><trkseg>{pts}</trkseg></trk></gpx>').encode()


def make_csv(rows):
    return "\n".join([HEADER] + rows)


def test_data_em_portugues_e_utc():
    assert parse_date("26 de out. de 2026, 15:05:43") == datetime(2026, 10, 26, 15, 5, 43, tzinfo=timezone.utc)
    assert parse_date("3 de mai. de 2025, 07:00:00").month == 5


def test_csv_usa_segundo_bloco_e_cadencia_por_perna():
    csv_text = make_csv(['1,"20 de out. de 2026, 10:00:00",Corrida,Corrida,600,"1,80",170,,600.0,590.0,1800.0,86.0,150.0',
                         '2,"20 de out. de 2026, 12:00:00",Passeio,Caminhada,600,"0,5",120,,600.0,600.0,500.0,110.0,100.0'])
    run, walk = read_activities_csv(csv_text)
    assert run.distance_m == 1800.0 and run.moving_s == 590.0
    assert run.avg_cadence_spm == 172.0          # corrida: dobra
    assert walk.avg_cadence_spm == 110.0         # caminhada: já é total
    assert run.sport == "run" and walk.sport == "walk"


def test_tcx_junta_linhas_do_mesmo_horario():
    tcx = b"""<?xml version="1.0"?><TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
    <Activities><Activity Sport="Run"><Id>2026-10-20T10:00:00Z</Id><Lap><Track>
    <Trackpoint><Time>2026-10-20T10:00:01Z</Time><HeartRateBpm><Value>120</Value></HeartRateBpm></Trackpoint>
    <Trackpoint><Time>2026-10-20T10:00:01Z</Time><Cadence>88</Cadence><Extensions><TPX><Speed>3.1</Speed></TPX></Extensions></Trackpoint>
    </Track></Lap></Activity></Activities></TrainingCenterDatabase>"""
    p = parse_activity_file("x.tcx.gz", gzip.compress(tcx))
    assert p.sport_hint == "Run" and len(p.points) == 1
    pt = p.points[0]
    assert (pt.hr, pt.cadence, pt.speed) == (120, 88, 3.1)


def test_parciais_e_ajuste_de_distancia():
    parsed = parse_activity_file("r.gpx", make_gpx(n=700, speed=3.0))
    res = process_points(parsed.points, "run", summary_distance_m=2000.0)
    assert [s["km"] for s in res.splits] == [1, 2]
    assert res.splits[0]["pace_s_km"] == pytest.approx(349, abs=3)   # ~2000 m em 699 s
    assert res.hr_quality == "ok"


def test_pico_isolado_de_fc_e_removido():
    parsed = parse_activity_file("r.gpx", make_gpx(n=300))
    parsed.points[100].hr = 205
    res = process_points(parsed.points, "run", None)
    assert res.samples[100].hr is None and res.samples[100].hr_raw == 205
    assert res.samples[101].hr == 150


def test_zonas_e_carga():
    parsed = parse_activity_file("r.gpx", make_gpx(n=601, hr=171))   # 171/190 = 90% -> z5
    res = process_points(parsed.points, "run", None)
    z = zones_from_samples(res.samples, 190)
    assert z["z5"] == pytest.approx(600, abs=1)
    assert trimp_from_zones(z) == pytest.approx(50, abs=0.2)          # 10 min x peso 5


def test_fitness_e_fadiga():
    s = daily_series({date(2026, 1, 1): 100.0}, end=date(2026, 1, 8))
    assert s[0].form == 0 and s[1].fatigue > s[1].fitness > 0
    assert s[1].form < 0   # dia seguinte ao treino: fadiga maior que fitness


@pytest.fixture
def engine(tmp_path):
    get_engine.cache_clear()
    eng = get_engine(f"sqlite:///{tmp_path}/t.db")
    init_db(eng)
    yield eng
    get_engine.cache_clear()


def test_importacao_zip_idempotente_e_duplicatas(engine, tmp_path):
    csv_text = make_csv([
        '10,"20 de out. de 2026, 10:00:00",Corrida A,Corrida,700,"2,00",160,activities/10.gpx.gz,700.0,699.0,2000.0,86.0,150.0',
        '11,"20 de out. de 2026, 10:03:00",Corrida A copia,Corrida,700,"2,00",160,,700.0,699.0,2000.0,86.0,150.0',
        '12,"21 de out. de 2026, 22:00:00",Noite,Corrida,700,"2,00",160,activities/nao_existe.tcx.gz,700.0,699.0,2000.0,,150.0',
    ])
    zpath = tmp_path / "export.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("export_123/activities.csv", csv_text)
        z.writestr("export_123/activities/10.gpx.gz", gzip.compress(make_gpx(n=700)))
    settings = Settings(fc_max=190, timezone="America/Sao_Paulo")
    for _ in range(2):
        with session_scope(engine) as s:
            rep = import_strava_export(s, zpath)
            services.recompute(s, settings)
    assert rep["atualizadas"] == 3
    with session_scope(engine) as s:
        acts = {a.source_id: a for a in s.scalars(select(Activity))}
        assert acts["10"].file_status == "ok" and len(acts["10"].splits) == 2
        assert acts["11"].possible_duplicate_of == acts["10"].id
        assert acts["12"].file_status == "ausente"
        # 22:00 UTC de 21/10 = 19:00 em São Paulo, mesmo dia
        assert acts["12"].start_utc.astimezone(settings.tz).date() == date(2026, 10, 21)
