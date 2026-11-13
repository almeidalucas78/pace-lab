"""Avisos ao usuário. No Windows vira notificação do sistema; em servidor (ou sem winotify) só vai para o log."""
from __future__ import annotations

import logging
import sys

log = logging.getLogger("treino")
APP_ID = "Treino"


def notify(title: str, message: str, enabled: bool = True) -> None:
    log.info("%s: %s", title, message)
    if not enabled or sys.platform != "win32":
        return
    try:
        from winotify import Notification
        Notification(app_id=APP_ID, title=title, msg=message).show()
    except Exception as e:  # notificação nunca derruba a sincronização
        log.warning("notificação do Windows falhou: %s", e)


def describe_new(activities: list[dict]) -> tuple[str, str] | None:
    """Título e texto para os treinos novos (resumos de services.activity_summary)."""
    if not activities:
        return None
    lines = []
    for a in activities[:3]:
        parts = [a["nome"] or a["esporte"], a["data"][11:16]]
        if a["distancia_km"]:
            parts.append(f"{a['distancia_km']:.2f} km")
        if a["ritmo"]:
            parts.append(a["ritmo"])
        if a["fc_media"]:
            parts.append(f"FC {a['fc_media']:.0f}")
        lines.append(", ".join(parts))
    if len(activities) > 3:
        lines.append(f"e mais {len(activities) - 3}")
    title = "Treino novo importado" if len(activities) == 1 else f"{len(activities)} treinos novos importados"
    return title, "\n".join(lines)
