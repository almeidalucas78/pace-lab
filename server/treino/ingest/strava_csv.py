"""Leitura do activities.csv do export do Strava.

Observações do export real:
- Datas em português ("26 de out. de 2026, 15:05:43") e em UTC.
- Várias colunas com nome repetido. O primeiro bloco é o "formatado" (distância em km com vírgula);
  o segundo bloco é numérico (distância em metros). Usamos sempre o segundo quando existir.
- Cadência de corrida vem por perna.
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime, timezone

PT_MONTHS = {"jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
             "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12}

# campo -> lista de (nome da coluna, ocorrência). Português primeiro; inglês como alternativa.
COLUMNS: dict[str, list[tuple[str, int]]] = {
    "id": [("ID da atividade", 0), ("Activity ID", 0)],
    "date": [("Data da atividade", 0), ("Activity Date", 0)],
    "name": [("Nome da atividade", 0), ("Activity Name", 0)],
    "type": [("Tipo de atividade", 0), ("Activity Type", 0)],
    "description": [("Descrição da atividade", 0), ("Activity Description", 0)],
    "elapsed_s": [("Tempo decorrido", 1), ("Elapsed Time", 1), ("Tempo decorrido", 0), ("Elapsed Time", 0)],
    "moving_s": [("Tempo de movimentação", 0), ("Moving Time", 0)],
    "distance_m": [("Distância", 1), ("Distance", 1)],
    "elev_gain_m": [("Ganho de elevação", 0), ("Elevation Gain", 0)],
    "max_hr": [("Frequência cardíaca máxima", 1), ("Max Heart Rate", 1), ("Frequência cardíaca máxima", 0)],
    "avg_hr": [("Frequência cardíaca média", 0), ("Average Heart Rate", 0)],
    "avg_cadence": [("Cadência média", 0), ("Average Cadence", 0)],
    "calories": [("Calorias", 0), ("Calories", 0)],
    "rpe": [("Percepção de esforço", 0), ("Perceived Exertion", 0)],
    "gear": [("Equipamento da atividade", 0), ("Activity Gear", 0)],
    "file": [("Nome do arquivo", 0), ("Filename", 0)],
    "temp_c": [("Temperatura atmosférica", 0), ("Weather Temperature", 0)],
    "humidity": [("Umidade", 0), ("Humidity", 0)],
}
REQUIRED = ("id", "date", "type")

SPORTS = {
    "corrida": "run", "run": "run", "corrida na esteira": "run", "virtual run": "run", "trail run": "run",
    "caminhada": "walk", "walk": "walk", "hike": "walk", "trilha": "walk",
    "pedalada": "ride", "ride": "ride", "virtual ride": "ride",
    "treinamento com peso": "strength", "weight training": "strength",
    "treino": "workout", "workout": "workout",
}


@dataclass
class CsvActivity:
    id: str
    start_utc: datetime
    sport: str
    sport_raw: str
    name: str | None
    description: str | None
    elapsed_s: float | None
    moving_s: float | None
    distance_m: float | None
    elev_gain_m: float | None
    max_hr: float | None
    avg_hr: float | None
    avg_cadence_spm: float | None
    calories: float | None
    rpe: float | None
    gear: str | None
    file: str | None
    temp_c: float | None
    humidity: float | None


def parse_date(s: str) -> datetime:
    s = s.strip()
    m = re.match(r"(\d{1,2}) de (\w{3})\.? de (\d{4}),? (\d{1,2}):(\d{2}):(\d{2})", s)
    if m:
        d, mon, y, hh, mm, ss = m.groups()
        return datetime(int(y), PT_MONTHS[mon.lower()], int(d), int(hh), int(mm), int(ss), tzinfo=timezone.utc)
    for fmt in ("%b %d, %Y, %I:%M:%S %p", "%b %d, %Y, %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"data em formato desconhecido: {s!r}")


def _num(s: str | None) -> float | None:
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return float(s.replace(",", ".")) if s.count(",") == 1 and "." not in s else float(s)
    except ValueError:
        return None


def _index(header: list[str]) -> dict[str, int]:
    positions: dict[tuple[str, int], int] = {}
    seen: dict[str, int] = {}
    for i, col in enumerate(header):
        n = seen.get(col, 0)
        positions[(col, n)] = i
        seen[col] = n + 1
    idx = {}
    for field_name, candidates in COLUMNS.items():
        for cand in candidates:
            if cand in positions:
                idx[field_name] = positions[cand]
                break
    missing = [f for f in REQUIRED if f not in idx]
    if missing:
        raise ValueError(f"activities.csv sem as colunas obrigatórias: {missing}")
    return idx


def normalize_sport(raw: str) -> str:
    return SPORTS.get(raw.strip().lower(), "other")


def read_activities_csv(text: str) -> list[CsvActivity]:
    reader = csv.reader(io.StringIO(text.lstrip("﻿"), newline=""))
    header = next(reader)
    idx = _index(header)

    def get(row, key):
        i = idx.get(key)
        return row[i] if i is not None and i < len(row) else None

    out = []
    for row in reader:
        if not row or not get(row, "id"):
            continue
        sport_raw = get(row, "type") or ""
        sport = normalize_sport(sport_raw)
        cad = _num(get(row, "avg_cadence"))
        if cad is not None and sport == "run":
            cad *= 2  # Strava exporta cadência de corrida por perna (caminhada já vem total)
        text_or_none = lambda v: (v.strip() or None) if v is not None else None
        out.append(CsvActivity(
            id=get(row, "id").strip(),
            start_utc=parse_date(get(row, "date")),
            sport=sport,
            sport_raw=sport_raw,
            name=text_or_none(get(row, "name")),
            description=text_or_none(get(row, "description")),
            elapsed_s=_num(get(row, "elapsed_s")),
            moving_s=_num(get(row, "moving_s")),
            distance_m=_num(get(row, "distance_m")),
            elev_gain_m=_num(get(row, "elev_gain_m")),
            max_hr=_num(get(row, "max_hr")),
            avg_hr=_num(get(row, "avg_hr")),
            avg_cadence_spm=cad,
            calories=_num(get(row, "calories")),
            rpe=_num(get(row, "rpe")),
            gear=text_or_none(get(row, "gear")),
            file=text_or_none(get(row, "file")),
            temp_c=_num(get(row, "temp_c")),
            humidity=_num(get(row, "humidity")),
        ))
    return out
