"""Importa o export completo do Strava (pasta descompactada ou o próprio .zip)."""
from __future__ import annotations

import gzip
import json
import zipfile
from collections import Counter
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import Activity
from .files import UnsupportedFormat, parse_activity_file
from .streams_store import save_streams
from .strava_csv import CsvActivity, read_activities_csv

MAX_JSON_BYTES = 2_000_000


class ExportSource:
    """Abstrai pasta ou zip: o resto do código só pede arquivos pelo caminho relativo."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.zip = zipfile.ZipFile(self.path) if self.path.is_file() else None
        self.prefix = ""
        if self.zip:
            names = self.zip.namelist()
            csv_name = next((n for n in names if n.endswith("activities.csv")), None)
            if csv_name is None:
                raise FileNotFoundError("activities.csv não encontrado dentro do zip")
            self.prefix = csv_name[: -len("activities.csv")]
        elif not (self.path / "activities.csv").exists():
            raise FileNotFoundError(f"activities.csv não encontrado em {self.path}")

    def read(self, rel: str) -> bytes | None:
        rel = rel.replace("\\", "/")
        if self.zip:
            try:
                return self.zip.read(self.prefix + rel)
            except KeyError:
                return None
        p = self.path / rel
        return p.read_bytes() if p.exists() else None


def _apply_summary(a: Activity, c: CsvActivity) -> None:
    a.sport, a.sport_raw, a.name, a.description = c.sport, c.sport_raw, c.name, c.description
    a.start_utc = c.start_utc
    a.elapsed_s, a.moving_s, a.distance_m = c.elapsed_s, c.moving_s, c.distance_m
    a.elev_gain_m, a.avg_hr, a.max_hr = c.elev_gain_m, c.avg_hr, c.max_hr
    a.avg_cadence_spm, a.calories, a.rpe, a.gear = c.avg_cadence_spm, c.calories, c.rpe, c.gear
    a.temp_c, a.humidity, a.file_path = c.temp_c, c.humidity, c.file


def _store_streams(session: Session, a: Activity, raw: bytes, c: CsvActivity) -> None:
    parsed = parse_activity_file(c.file, raw)
    save_streams(session, a, parsed.points, parsed.fmt)


def _store_json(a: Activity, raw: bytes, name: str) -> None:
    data = gzip.decompress(raw) if name.endswith(".gz") else raw
    extra = dict(a.extra or {})
    if len(data) <= MAX_JSON_BYTES:
        extra["detalhe_bruto"] = json.loads(data)
    else:
        extra["aviso"] = f"JSON com {len(data)} bytes, não armazenado"
    extra["formato"] = "json"
    a.extra = extra
    a.file_status = "ok"


def import_strava_export(session: Session, path: str | Path, with_streams: bool = True, progress=None) -> dict:
    src = ExportSource(path)
    raw_csv = src.read("activities.csv")
    rows = read_activities_csv(raw_csv.decode("utf-8-sig"))
    status = Counter()
    errors: list[str] = []

    for n, c in enumerate(rows, 1):
        a = session.scalar(select(Activity).where(Activity.source == "strava", Activity.source_id == c.id))
        is_new = a is None
        if is_new:
            a = Activity(source="strava", source_id=c.id)
            session.add(a)
        _apply_summary(a, c)
        a.file_error = None
        session.flush()  # garante a.id

        if not c.file:
            a.file_status = "sem_arquivo"
        elif not with_streams:
            pass
        else:
            raw = src.read(c.file)
            if raw is None:
                a.file_status = "ausente"
            else:
                try:
                    if c.file.endswith((".json", ".json.gz")):
                        _store_json(a, raw, c.file)
                    else:
                        _store_streams(session, a, raw, c)
                except UnsupportedFormat:
                    a.file_status = "nao_suportado"
                except Exception as e:  # um arquivo ruim não derruba a importação
                    a.file_status, a.file_error = "erro", f"{type(e).__name__}: {e}"
                    errors.append(f"{c.file}: {a.file_error}")
        status["novas" if is_new else "atualizadas"] += 1
        status[f"arquivo_{a.file_status}"] += 1
        if progress:
            progress(n, len(rows))
    session.flush()
    return {"atividades": len(rows), **status, "erros": errors}
