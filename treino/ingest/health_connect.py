"""Converte o JSON do app HC Webhook (servidor local ou webhook) em sessões de treino.

Formato segundo a documentação do app (docs/webhook.md). Ainda não conferido com um JSON real:
- `exercise`: type, start_time, end_time, duration_seconds, distance_meters, steps, avg/max_cadence_spm,
  stride_length_m e metadata.id (id do registro no Health Connect).
- `heart_rate`: amostras {"bpm", "time"} ou, se o app agrega, {"avg", "min", "max", "time"}.
- `distance`, `total_calories`, `active_calories`: intervalos com start_time e end_time.
- `deleted`: [{"type", "id"}] de registros apagados no Health Connect.
- Horários em UTC ("Z") ou hora local com deslocamento, conforme a configuração do app.
A sessão não traz GPS, velocidade nem potência.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timezone
from statistics import median

from .files import Point

SPORTS = {
    "RUNNING": "run", "RUNNING_TREADMILL": "run",
    "WALKING": "walk", "HIKING": "walk",
    "BIKING": "ride", "BIKING_STATIONARY": "ride",
    "STRENGTH_TRAINING": "strength", "WEIGHTLIFTING": "strength",
}
# Distância por ponto só quando os registros de distância são curtos; senão as parciais seriam inventadas.
MAX_DIST_INTERVAL_S = 120
MIN_DIST_RECORDS = 3


@dataclass
class HCSession:
    source_id: str
    sport: str
    sport_raw: str
    start_utc: datetime
    end_utc: datetime
    duration_s: float | None
    distance_m: float | None
    steps: int | None
    avg_cadence_spm: float | None
    max_cadence_spm: float | None
    calories: float | None
    avg_hr: float | None
    max_hr: float | None
    origin: str | None
    device: dict | None
    points: list[Point] = field(default_factory=list)
    notes: dict = field(default_factory=dict)


@dataclass
class HCPayload:
    sessions: list[HCSession]
    deleted_exercise_ids: list[str]


def parse_time(s: str | int | float) -> datetime:
    if isinstance(s, (int, float)):
        return datetime.fromtimestamp(s / 1000, tz=timezone.utc)
    dt = datetime.fromisoformat(str(s).strip().replace("Z", "+00:00"))
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def normalize_sport(raw: str) -> str:
    key = str(raw).strip().upper().removeprefix("EXERCISE_TYPE_")
    return SPORTS.get(key, "other")


def _hr_series(records: list[dict]) -> tuple[list[tuple[datetime, float]], bool]:
    """(horário, bpm) ordenados. O segundo valor indica se o app mandou médias por bloco em vez de amostras."""
    out, aggregated = [], False
    for r in records:
        if "time" not in r:
            continue
        if any(k in r for k in ("avg", "min", "max")):
            aggregated = True
            v = r.get("avg", r.get("bpm"))
        else:
            v = r.get("bpm")
        if v is not None:
            out.append((parse_time(r["time"]), float(v)))
    out.sort(key=lambda x: x[0])
    return out, aggregated


def _intervals(records: list[dict], value_key: str) -> list[tuple[datetime, datetime, float]]:
    out = []
    for r in records:
        if "start_time" in r and "end_time" in r and r.get(value_key) is not None:
            out.append((parse_time(r["start_time"]), parse_time(r["end_time"]), float(r[value_key])))
    out.sort(key=lambda x: x[0])
    return out


def _inside(intervals, start: datetime, end: datetime):
    return [iv for iv in intervals if iv[0] >= start and iv[1] <= end]


def _distance_curve(intervals) -> list[tuple[datetime, float]] | None:
    """Distância acumulada no fim de cada registro, se os registros forem curtos o bastante."""
    if len(intervals) < MIN_DIST_RECORDS:
        return None
    if median((b - a).total_seconds() for a, b, _ in intervals) > MAX_DIST_INTERVAL_S:
        return None
    curve, total = [(intervals[0][0], 0.0)], 0.0
    for _, end, meters in intervals:
        total += meters
        curve.append((end, total))
    return curve


def _interpolate(curve: list[tuple[datetime, float]], t: datetime) -> float:
    times = [c[0] for c in curve]
    i = bisect_left(times, t)
    if i == 0:
        return curve[0][1]
    if i >= len(curve):
        return curve[-1][1]
    (t0, d0), (t1, d1) = curve[i - 1], curve[i]
    span = (t1 - t0).total_seconds()
    return d0 if span <= 0 else d0 + (d1 - d0) * (t - t0).total_seconds() / span


def parse_payload(payload: dict) -> HCPayload:
    hr, hr_aggregated = _hr_series(payload.get("heart_rate") or [])
    hr_times = [t for t, _ in hr]
    distances = _intervals(payload.get("distance") or [], "meters")
    calories = _intervals(payload.get("total_calories") or payload.get("active_calories") or [], "calories")

    sessions = []
    for ex in payload.get("exercise") or []:
        if "start_time" not in ex or "end_time" not in ex:
            continue
        start, end = parse_time(ex["start_time"]), parse_time(ex["end_time"])
        meta = ex.get("metadata") or {}
        raw_type = str(ex.get("type", ""))
        source_id = meta.get("id") or f"{raw_type}:{start.isoformat()}"
        notes: dict = {"fc_resolucao": "agregada" if hr_aggregated else "amostras"}

        i, j = bisect_left(hr_times, start), bisect_right(hr_times, end)
        sess_hr = hr[i:j]
        sess_dist = _inside(distances, start, end)
        curve = _distance_curve(sess_dist)
        notes["distancia_por_ponto"] = curve is not None
        if sess_dist and curve is None:
            notes["aviso_distancia"] = "registros de distância longos demais para parciais por km"

        points = [Point(time=t, hr=v, dist=_interpolate(curve, t) if curve else None) for t, v in sess_hr]
        if curve:
            hr_set = set(hr_times[i:j])
            points += [Point(time=t, dist=d) for t, d in curve if t not in hr_set]
            points.sort(key=lambda p: p.time)

        distance = ex.get("distance_meters")
        if distance is None and sess_dist:
            distance = sum(m for _, _, m in sess_dist)
        cal = sum(c for _, _, c in _inside(calories, start, end)) or None
        hr_vals = [v for _, v in sess_hr]
        sessions.append(HCSession(
            source_id=str(source_id), sport=normalize_sport(raw_type), sport_raw=raw_type,
            start_utc=start, end_utc=end,
            duration_s=ex.get("duration_seconds") or (end - start).total_seconds(),
            distance_m=float(distance) if distance is not None else None,
            steps=ex.get("steps"), avg_cadence_spm=ex.get("avg_cadence_spm"), max_cadence_spm=ex.get("max_cadence_spm"),
            calories=cal,
            avg_hr=round(sum(hr_vals) / len(hr_vals), 1) if hr_vals else None,
            max_hr=max(hr_vals) if hr_vals else None,
            origin=meta.get("data_origin"), device=meta.get("device"),
            points=points, notes=notes))

    deleted = [str(d["id"]) for d in payload.get("deleted") or [] if d.get("type") == "exercise" and d.get("id")]
    return HCPayload(sessions=sessions, deleted_exercise_ids=deleted)
