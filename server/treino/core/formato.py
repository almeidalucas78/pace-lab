"""Formatação de valores para leitura humana."""

from __future__ import annotations


def pace_str(seconds_per_km: float | None) -> str | None:
    if not seconds_per_km:
        return None
    m, s = divmod(round(seconds_per_km), 60)
    return f"{m}:{s:02d}/km"
