"""Zonas de FC, carga por treino (TRIMP de Edwards) e fitness/fadiga/forma diários."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

# Limites em % da FC máxima. z0 = abaixo de 50% (não conta carga).
ZONES = [("z0", 0.0), ("z1", 0.50), ("z2", 0.60), ("z3", 0.70), ("z4", 0.80), ("z5", 0.90)]
ZONE_WEIGHT = {"z0": 0, "z1": 1, "z2": 2, "z3": 3, "z4": 4, "z5": 5}
FITNESS_DAYS, FATIGUE_DAYS = 42, 7
ENDURANCE_SPORTS = ("run", "walk", "ride")


def zone_for(hr: float, fc_max: float) -> str:
    frac = hr / fc_max
    name = "z0"
    for z, lo in ZONES:
        if frac >= lo:
            name = z
    return name


def zones_from_samples(samples, fc_max: float) -> dict[str, float]:
    """Segundos em cada zona, usando o intervalo até a próxima leitura (limitado a 5 s)."""
    out = {z: 0.0 for z, _ in ZONES}
    hr_samples = [s for s in samples if s.hr is not None]
    for a, b in zip(hr_samples, hr_samples[1:]):
        dt = min(b.t_s - a.t_s, 5.0)
        if dt > 0:
            out[zone_for(a.hr, fc_max)] += dt
    return {k: round(v, 1) for k, v in out.items()}


def trimp_from_zones(zones_s: dict[str, float]) -> float:
    return round(sum(ZONE_WEIGHT[z] * s / 60 for z, s in zones_s.items()), 1)


def trimp_from_average(avg_hr: float, moving_s: float, fc_max: float) -> float:
    return round(ZONE_WEIGHT[zone_for(avg_hr, fc_max)] * moving_s / 60, 1)


def estimate_fc_max(rolling_maxes: list[float]) -> float | None:
    """Recebe, por treino, o maior valor da média móvel de 30 s da FC. Usa o maior deles."""
    vals = sorted(v for v in rolling_maxes if v)
    return round(vals[-1]) if vals else None


def rolling_max(samples, window_s: float = 30) -> float | None:
    hr = [(s.t_s, s.hr) for s in samples if s.hr is not None]
    best, j, acc = None, 0, 0.0
    for i, (t, v) in enumerate(hr):
        acc += v
        while hr[j][0] < t - window_s:
            acc -= hr[j][1]
            j += 1
        n = i - j + 1
        if hr[i][0] - hr[j][0] >= window_s * 0.8 and n:
            m = acc / n
            best = m if best is None or m > best else best
    return best


@dataclass
class DayLoad:
    day: date
    trimp: float
    fitness: float
    fatigue: float
    form: float


def daily_series(trimp_by_day: dict[date, float], end: date | None = None) -> list[DayLoad]:
    if not trimp_by_day:
        return []
    start = min(trimp_by_day)
    end = end or max(trimp_by_day)
    kf = 1 - math.exp(-1 / FITNESS_DAYS)
    ka = 1 - math.exp(-1 / FATIGUE_DAYS)
    fit = fat = 0.0
    out = []
    d = start
    while d <= end:
        form = fit - fat  # forma do dia = estado ao acordar (antes do treino do dia)
        t = trimp_by_day.get(d, 0.0)
        fit += (t - fit) * kf
        fat += (t - fat) * ka
        out.append(DayLoad(d, round(t, 1), round(fit, 1), round(fat, 1), round(form, 1)))
        d += timedelta(days=1)
    return out
