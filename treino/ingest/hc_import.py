"""Grava no banco as sessões lidas do Health Connect. Idempotente pelo id do registro no Health Connect."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db.models import Activity
from .health_connect import HCPayload, HCSession
from .streams_store import save_streams

SOURCE = "health_connect"
NAMES = {"run": "Corrida", "walk": "Caminhada", "ride": "Pedalada", "strength": "Musculação"}


def _apply(a: Activity, s: HCSession) -> None:
    a.sport, a.sport_raw = s.sport, s.sport_raw
    a.name = a.name or NAMES.get(s.sport, "Treino")
    a.start_utc = s.start_utc
    a.elapsed_s = (s.end_utc - s.start_utc).total_seconds()
    a.moving_s = s.duration_s  # o Health Connect não informa pausas
    a.distance_m, a.calories = s.distance_m, s.calories
    a.avg_hr, a.max_hr = s.avg_hr, s.max_hr
    a.avg_cadence_spm = s.avg_cadence_spm
    a.extra = {"origem_app": s.origin, "dispositivo": s.device, "passos": s.steps,
               "cadencia_max": s.max_cadence_spm}


def import_payload(session: Session, payload: HCPayload) -> dict:
    new_ids, updated = [], 0
    for s in payload.sessions:
        a = session.scalar(select(Activity).where(Activity.source == SOURCE, Activity.source_id == s.source_id))
        if a is None:
            a = Activity(source=SOURCE, source_id=s.source_id)
            session.add(a)
            is_new = True
        else:
            is_new = False
        _apply(a, s)
        session.flush()
        if s.points:
            save_streams(session, a, s.points, "health_connect", s.notes)
        else:
            a.file_status, a.hr_quality = "sem_arquivo", "sem_fc"
            a.extra = {**(a.extra or {}), **s.notes}
        if is_new:
            new_ids.append(a.id)
        else:
            updated += 1
    removed = 0
    if payload.deleted_exercise_ids:
        removed = session.execute(delete(Activity).where(
            Activity.source == SOURCE, Activity.source_id.in_(payload.deleted_exercise_ids))).rowcount
    session.flush()
    return {"novas_ids": new_ids, "atualizadas": updated, "apagadas": removed}
