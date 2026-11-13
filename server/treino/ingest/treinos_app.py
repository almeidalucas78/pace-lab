"""Treinos enviados pelo app Android (ADR 0013), independente da fonte no celular.

Formato próprio e simples, pensado a partir do Samsung Health Data SDK (`ExerciseSession`, `ExerciseLog`,
`ExerciseLocation`), que serve também para o Health Connect no futuro:
- resumo: id na fonte, tipo, início, fim, duração, distância, calorias, FC média e máxima, cadência média;
- registros ao longo do treino: horário (ms), FC, velocidade (m/s), cadência (passos/min), potência;
- percurso: horário (ms), latitude, longitude, altitude.

`converter` é cálculo puro; `gravar` grava no banco, idempotente pelo (fonte, id).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db.models import Activity
from .files import Point
from .streams_store import save_streams

FONTES = ("samsung_health", "health_connect")
NOMES = {"run": "Corrida", "walk": "Caminhada", "ride": "Pedalada", "strength": "Musculação"}

# tipos do Samsung Health Data SDK (DataType.ExerciseType.PredefinedExerciseType, conferidos no SDK 1.1.0)
ESPORTES = {
    "RUNNING": "run", "TRACK_RUNNING": "run", "TREADMILL": "run",
    "WALKING": "walk", "HIKING": "walk", "BACKPACKING": "walk",
    "BIKING": "ride", "MOUNTAIN_BIKING": "ride", "STATIONARY_BIKING": "ride",
    "WEIGHT_MACHINE": "strength", "BENCH_PRESS": "strength", "SQUATS": "strength", "DEADLIFTS": "strength",
    "LUNGES": "strength", "LEG_PRESSES": "strength", "LAT_PULLDOWNS": "strength", "SHOULDER_PRESSES": "strength",
    "ARM_CURLS": "strength", "CIRCUIT_TRAINING": "workout",
}


@dataclass
class TreinoRecebido:
    fonte: str
    id: str
    esporte: str
    tipo_original: str
    inicio: datetime
    fim: datetime
    duracao_s: float | None = None
    distancia_m: float | None = None
    calorias: float | None = None
    fc_media: float | None = None
    fc_max: float | None = None
    cadencia_media: float | None = None
    ganho_elevacao_m: float | None = None
    titulo: str | None = None
    extras: dict = field(default_factory=dict)
    pontos: list[Point] = field(default_factory=list)


def esporte(tipo: str) -> str:
    return ESPORTES.get(str(tipo).strip().upper(), "other")


def _ms(t: int | float) -> datetime:
    return datetime.fromtimestamp(t / 1000, tz=timezone.utc)


def _positivo(v):
    return v if v is not None and v > 0 else None


def juntar_pontos(registros: list[dict], percurso: list[dict]) -> list[Point]:
    """Une registros (FC, velocidade, cadência) e percurso (GPS) pelo horário, em ordem."""
    pontos = [Point(time=_ms(r["t"]), hr=_positivo(r.get("fc")),   # o relógio grava 0 quando perde a FC
                    speed=r.get("vel"), cadence=_positivo(r.get("cad"))) for r in registros]
    pontos += [Point(time=_ms(g["t"]), lat=g["lat"], lon=g["lon"], ele=g.get("alt"))
               for g in percurso if gps_valido(g["lat"], g["lon"])]
    return mesclar_proximos(pontos)


JANELA_MESCLA_S = 0.5


CAMPOS_MESCLA = ("lat", "hr", "speed", "cadence")   # lon e ele andam junto com lat


def mesclar_proximos(pontos: list[Point]) -> list[Point]:
    """O Samsung Health grava GPS, FC e velocidade/cadência em registros e horários próprios, a frações de
    segundo uns dos outros. Separados, viram pontos intercalados. Junta cada ponto ao anterior quando estão
    a menos de 0,5 s e nenhum campo aparece nos dois (nada é sobrescrito)."""
    out: list[Point] = []
    for p in sorted(pontos, key=lambda x: x.time):
        q = out[-1] if out else None
        if (q is not None and (p.time - q.time).total_seconds() < JANELA_MESCLA_S
                and not any(getattr(q, c) is not None and getattr(p, c) is not None for c in CAMPOS_MESCLA)):
            if p.lat is not None:
                q.lat, q.lon, q.ele = p.lat, p.lon, p.ele
            for c in ("hr", "speed", "cadence"):
                if getattr(p, c) is not None:
                    setattr(q, c, getattr(p, c))
            continue
        out.append(Point(time=p.time, lat=p.lat, lon=p.lon, ele=p.ele, hr=p.hr,
                         cadence=p.cadence, speed=p.speed, dist=p.dist))
    return out


def gps_valido(lat: float | None, lon: float | None) -> bool:
    """O Samsung Health manda (0, 0) em esteira e musculação (treino sem GPS); (0, 0) fica no oceano."""
    return lat is not None and lon is not None and not (lat == 0 and lon == 0)


def converter(fonte: str, treino: dict) -> TreinoRecebido:
    """`treino` já validado pela API (horários de início e fim com fuso)."""
    extras = {k: treino[k] for k in ("vo2max",) if treino.get(k) is not None}
    pontos = juntar_pontos(treino.get("registros") or [], treino.get("percurso") or [])
    extras["pontos_gps"] = sum(1 for g in treino.get("percurso") or [] if gps_valido(g["lat"], g["lon"]))
    extras["registros"] = len(treino.get("registros") or [])
    return TreinoRecebido(
        fonte=fonte, id=str(treino["id"]), esporte=esporte(treino["tipo"]), tipo_original=str(treino["tipo"]),
        inicio=treino["inicio"].astimezone(timezone.utc), fim=treino["fim"].astimezone(timezone.utc),
        duracao_s=treino.get("duracao_s"), distancia_m=treino.get("distancia_m"), calorias=treino.get("calorias"),
        fc_media=treino.get("fc_media"), fc_max=treino.get("fc_max"), cadencia_media=treino.get("cadencia_media"),
        ganho_elevacao_m=treino.get("ganho_elevacao_m"), titulo=treino.get("titulo"), extras=extras, pontos=pontos)


def _aplicar(a: Activity, t: TreinoRecebido) -> None:
    a.sport, a.sport_raw = t.esporte, t.tipo_original
    a.name = t.titulo or a.name or NOMES.get(t.esporte, "Treino")
    a.start_utc = t.inicio
    a.elapsed_s = (t.fim - t.inicio).total_seconds()
    a.moving_s = t.duracao_s or a.elapsed_s
    a.distance_m, a.calories = t.distancia_m, t.calorias
    a.avg_hr, a.max_hr = t.fc_media, t.fc_max
    a.avg_cadence_spm, a.elev_gain_m = t.cadencia_media, t.ganho_elevacao_m
    a.extra = {"fonte_app": t.fonte, **t.extras}


def gravar(session: Session, treinos: list[TreinoRecebido], apagados: list[tuple[str, str]] | None = None) -> dict:
    """Grava ou atualiza cada treino; `apagados` = pares (fonte, id) removidos no celular."""
    novos, atualizados = [], 0
    for t in treinos:
        a = session.scalar(select(Activity).where(Activity.source == t.fonte, Activity.source_id == t.id))
        novo = a is None
        if novo:
            a = Activity(source=t.fonte, source_id=t.id)
            session.add(a)
        _aplicar(a, t)
        session.flush()
        if t.pontos:
            save_streams(session, a, t.pontos, t.fonte)
        else:
            a.file_status, a.hr_quality = "sem_arquivo", "sem_fc"
        if novo:
            novos.append(a.id)
        else:
            atualizados += 1
    removidos = 0
    for fonte, id_ in apagados or []:
        removidos += session.execute(delete(Activity).where(Activity.source == fonte,
                                                            Activity.source_id == id_)).rowcount
    session.flush()
    return {"novos_ids": novos, "atualizados": atualizados, "apagados": removidos}
