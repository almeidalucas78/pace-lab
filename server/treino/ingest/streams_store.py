"""Grava os pontos de um treino (amostras, parciais e notas de qualidade). Usado por todas as fontes."""

from __future__ import annotations

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from ..core.load import rolling_max
from ..core.streams import process_points
from ..db.models import Activity, Sample, Split
from .files import Point


def save_streams(session: Session, a: Activity, points: list[Point], fmt: str, notes: dict | None = None) -> None:
    res = process_points(points, a.sport, a.distance_m)
    session.execute(delete(Sample).where(Sample.activity_id == a.id))
    session.execute(delete(Split).where(Split.activity_id == a.id))
    if res.samples:
        session.execute(insert(Sample), [dict(activity_id=a.id, **s.__dict__) for s in res.samples])
    if res.splits:
        session.execute(insert(Split), [dict(activity_id=a.id, **sp) for sp in res.splits])
    session.expire(a, ["samples", "splits"])
    a.hr_quality, a.hr_suspect_pct = res.hr_quality, res.hr_suspect_pct
    extra = dict(a.extra or {})
    extra.update(res.notes)
    extra.update(notes or {})
    extra["formato"] = fmt
    extra["fc_30s_max"] = rolling_max(res.samples)
    if a.avg_cadence_spm is None:
        cads = [s.cadence_spm for s in res.samples if s.cadence_spm]
        if cads:
            a.avg_cadence_spm = round(sum(cads) / len(cads), 1)
    a.extra = extra
    a.file_status = "ok"
