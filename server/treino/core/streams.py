"""Transforma os pontos brutos de um arquivo em amostras limpas, splits e indicadores de qualidade.

Python puro, sem banco: recebe listas e devolve listas/dicts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from statistics import median

from ..ingest.files import Point

MOVING_SPEED = {"run": 0.9, "walk": 0.4, "ride": 1.5}  # m/s mínimos para contar como "em movimento"
MAX_GAP_S = 15  # intervalo maior que isso entre leituras = pausa
JANELA_MOVIMENTO_S = 3  # janela para decidir se está em movimento (parciais)
MAX_GPS_SPEED = 12.0  # m/s; acima disso o trecho é salto de GPS
HR_MIN, HR_MAX_ABS = 30, 230
HR_SPIKE_BPM, HR_SPIKE_WINDOW_S = 25, 2


@dataclass
class CleanSample:
    t_s: float
    lat: float | None
    lon: float | None
    ele_m: float | None
    hr: float | None
    hr_raw: float | None
    cadence_spm: float | None
    speed_ms: float | None
    dist_m: float | None


@dataclass
class StreamResult:
    samples: list[CleanSample]
    splits: list[dict]
    hr_quality: str
    hr_suspect_pct: float | None
    notes: dict = field(default_factory=dict)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _cumulative_distance(points: list[Point]) -> tuple[list[float | None], str]:
    """Usa a distância do arquivo quando existe em quase todos os pontos; senão calcula pelo GPS."""
    with_dist = sum(1 for p in points if p.dist is not None)
    if points and with_dist >= 0.8 * len(points):
        do_arquivo: list[float | None] = []
        last = 0.0
        for p in points:
            last = p.dist if p.dist is not None else last
            do_arquivo.append(last)
        return do_arquivo, "arquivo"
    out: list[float | None] = []
    total = 0.0
    prev: tuple[float, float, datetime] | None = None  # último ponto com GPS
    for p in points:
        if p.lat is not None and p.lon is not None:
            if prev is not None:
                d = haversine(prev[0], prev[1], p.lat, p.lon)
                dt = (p.time - prev[2]).total_seconds()
                if dt > 0 and d / dt <= MAX_GPS_SPEED:
                    total += d
            prev = (p.lat, p.lon, p.time)
        out.append(total if prev is not None else None)
    has_gps = any(p.lat is not None for p in points)
    if has_gps:
        return out, "gps"
    # sem GPS (esteira, treino indoor): integra a velocidade, se o arquivo trouxer
    if sum(1 for p in points if p.speed is not None) >= 0.5 * len(points):
        pela_vel: list[float | None] = []
        total, anterior = 0.0, None
        for p in points:
            if anterior is not None and p.speed is not None:
                dt = (p.time - anterior.time).total_seconds()
                if 0 < dt <= MAX_GAP_S:  # pausa ou falha de leitura não soma distância
                    total += p.speed * dt
            anterior = p
            pela_vel.append(total)
        return pela_vel, "velocidade"
    return [None] * len(points), "nenhuma"


def _cadence_factor(points: list[Point], sport: str) -> float:
    cads = [p.cadence for p in points if p.cadence]
    if sport == "run" and cads and median(cads) < 120:
        return 2.0  # arquivo grava por perna
    return 1.0


def _clean_hr(samples: list[CleanSample]) -> tuple[int, int]:
    """Remove leituras fora da faixa e picos isolados. Retorna (removidas, total com FC)."""
    total = removed = 0
    hr_idx = [i for i, s in enumerate(samples) if s.hr_raw is not None]
    for i in hr_idx:
        total += 1
        v = samples[i].hr_raw
        if v is None:
            continue
        if v < HR_MIN or v > HR_MAX_ABS:
            samples[i].hr = None
            removed += 1
    # pico isolado: salta e volta em poucos segundos
    for a, b, c in zip(hr_idx, hr_idx[1:], hr_idx[2:]):
        sa, sb, sc = samples[a], samples[b], samples[c]
        if sa.hr is None or sb.hr is None or sc.hr is None:
            continue
        if (
            sb.t_s - sa.t_s <= HR_SPIKE_WINDOW_S
            and sc.t_s - sb.t_s <= HR_SPIKE_WINDOW_S
            and abs(sb.hr - sa.hr) >= HR_SPIKE_BPM
            and abs(sb.hr - sc.hr) >= HR_SPIKE_BPM
        ):
            sb.hr = None
            removed += 1
    return removed, total


def _cadence_lock_pct(samples: list[CleanSample]) -> float | None:
    """% do tempo em esforço em que a FC fica colada na cadência (artefato comum de sensor óptico)."""
    last_cad, close, considered = None, 0, 0
    for s in samples:
        if s.cadence_spm:
            last_cad = s.cadence_spm
        if s.hr is not None and s.hr >= 140 and last_cad:
            considered += 1
            if abs(s.hr - last_cad) <= 3:
                close += 1
    return (100 * close / considered) if considered >= 120 else None


def _dist(s: CleanSample) -> float:
    """Distância de uma amostra que já se sabe ter distância (filtrada antes)."""
    assert s.dist_m is not None
    return s.dist_m


def _splits(samples: list[CleanSample], sport: str) -> list[dict]:
    thr = MOVING_SPEED.get(sport, 0.9)
    splits: list[dict] = []
    km = 1
    start_d = 0.0
    acc_t = 0.0
    hr_sum = hr_t = 0.0
    ele_start = next((s.ele_m for s in samples if s.ele_m is not None), None)
    com_dist = [s for s in samples if s.dist_m is not None]
    j = 0
    prev: CleanSample | None = None
    for i, s in enumerate(com_dist):
        # velocidade numa janela de alguns segundos: com leituras intercaladas (GPS e sensores em horários
        # próprios), dois pontos colados dão "3 m em 0,1 s" e "0 m em 0,9 s", e o par sozinho engana
        while s.t_s - com_dist[j].t_s > JANELA_MOVIMENTO_S:
            j += 1
        if prev is not None:
            a = com_dist[j] if j < i else prev
            dt = s.t_s - prev.t_s
            vel = (_dist(s) - _dist(a)) / (s.t_s - a.t_s) if s.t_s > a.t_s else 0.0
            if 0 < dt <= MAX_GAP_S and vel >= thr:
                acc_t += dt
                if s.hr is not None:
                    hr_sum += s.hr * dt
                    hr_t += dt
        while _dist(s) - start_d >= 1000:
            ele_now = s.ele_m
            splits.append(
                dict(
                    km=km,
                    distance_m=1000.0,
                    moving_s=acc_t,
                    pace_s_km=acc_t if acc_t else None,
                    avg_hr=(hr_sum / hr_t) if hr_t else None,
                    elev_delta_m=(ele_now - ele_start) if (ele_now is not None and ele_start is not None) else None,
                )
            )
            km += 1
            start_d += 1000
            acc_t = hr_sum = hr_t = 0.0
            ele_start = ele_now
        prev = s
    if prev is not None and _dist(prev) - start_d >= 20 and acc_t > 0:
        d = _dist(prev) - start_d
        splits.append(
            dict(
                km=km,
                distance_m=d,
                moving_s=acc_t,
                pace_s_km=acc_t / (d / 1000),
                avg_hr=(hr_sum / hr_t) if hr_t else None,
                elev_delta_m=(prev.ele_m - ele_start) if (prev.ele_m is not None and ele_start is not None) else None,
            )
        )
    return splits


def process_points(points: list[Point], sport: str, summary_distance_m: float | None) -> StreamResult:
    points = sorted(points, key=lambda p: p.time)
    if not points:
        return StreamResult([], [], "sem_fc", None, {"aviso": "arquivo sem pontos"})
    t0 = points[0].time
    dist, dist_src = _cumulative_distance(points)
    notes: dict = {"distancia_fonte": dist_src}

    # Ajusta a distância do stream ao total oficial (o Strava corrige o GPS; ficamos coerentes com ele)
    stream_total = next((d for d in reversed(dist) if d is not None), None)
    if stream_total and summary_distance_m:
        ratio = summary_distance_m / stream_total
        notes["fator_distancia"] = round(ratio, 4)
        if 0.85 <= ratio <= 1.15:
            dist = [d * ratio if d is not None else None for d in dist]
        else:
            notes["aviso_distancia"] = "distância do arquivo difere mais de 15% do resumo; mantida a do arquivo"

    cad_factor = _cadence_factor(points, sport)
    samples = [
        CleanSample(
            t_s=(p.time - t0).total_seconds(),
            lat=p.lat,
            lon=p.lon,
            ele_m=p.ele,
            hr=p.hr,
            hr_raw=p.hr,
            cadence_spm=(p.cadence * cad_factor) if p.cadence else None,
            speed_ms=p.speed,
            dist_m=d,
        )
        for p, d in zip(points, dist)
    ]

    # velocidade derivada quando o arquivo não traz
    if not any(s.speed_ms for s in samples):
        for i, s in enumerate(samples):
            j = i
            while j > 0 and s.t_s - samples[j - 1].t_s <= 5:
                j -= 1
            a = samples[j]
            if j != i and a.dist_m is not None and s.dist_m is not None:
                s.speed_ms = (s.dist_m - a.dist_m) / (s.t_s - a.t_s)

    removed, total_hr = _clean_hr(samples)
    if total_hr == 0:
        quality, pct = "sem_fc", None
    else:
        pct = 100 * removed / total_hr
        lock = _cadence_lock_pct(samples)
        notes["fc_colada_cadencia_pct"] = round(lock, 1) if lock is not None else None
        if lock is not None and lock >= 40:
            quality = "suspeita_cadencia"
        elif pct >= 5:
            quality = "suspeita"
        else:
            quality = "ok"
    return StreamResult(
        samples=samples, splits=_splits(samples, sport), hr_quality=quality, hr_suspect_pct=pct, notes=notes
    )
