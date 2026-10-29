"""Agendador dentro do próprio serviço (funciona igual no PC e num servidor).

Sincroniza ao iniciar, para recuperar o período com o PC desligado, e depois a cada SYNC_INTERVALO_MIN.
"""
from __future__ import annotations

import logging
import threading

from . import services
from .config import Settings
from .db import session_scope
from .ingest.hc_client import HCClient
from .notify import describe_new, notify

log = logging.getLogger("treino")


def run_sync(settings: Settings) -> dict:
    """Uma rodada: sincroniza e avisa os treinos novos. Usado pelo agendador, pela CLI e pela API."""
    client = HCClient(settings.hc_url, settings.hc_token, settings.hc_timeout_s)
    with session_scope() as s:
        rep = services.sync_health_connect(s, settings, client)
    if rep["status"] == "ok":
        msg = describe_new(rep["novos"])
        if msg:
            notify(*msg, enabled=settings.notificacoes)
    else:
        log.warning("sincronização falhou: %s", rep.get("erro"))
    return rep


class SyncScheduler:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._stop = threading.Event()
        self._lock = threading.Lock()  # nunca duas rodadas ao mesmo tempo
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.settings.hc_url:
            log.warning("HC_URL vazio no .env: sincronização automática desligada")
            return
        self._thread = threading.Thread(target=self._loop, name="sync-health-connect", daemon=True)
        self._thread.start()
        log.info("sincronização automática a cada %s min", self.settings.sync_intervalo_min)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def run_now(self) -> dict:
        with self._lock:
            return run_sync(self.settings)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.run_now()
            except Exception:
                log.exception("erro inesperado na sincronização")
            self._stop.wait(self.settings.sync_intervalo_min * 60)
