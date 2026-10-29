"""Cliente do servidor HTTP local do app HC Webhook (celular na mesma rede).

Endpoints usados (docs/local-http.md do app): `GET /ping` e `GET /?start=...&end=...`.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx


class HCUnavailable(Exception):
    """Celular fora da rede, app parado ou resposta inválida."""


class HCClient:
    def __init__(self, base_url: str, token: str = "", timeout_s: float = 60):
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.timeout = timeout_s

    def _get(self, path: str, params: dict | None = None, timeout: float | None = None) -> dict:
        try:
            r = httpx.get(self.base_url + path, params=params, headers=self.headers,
                          timeout=timeout or self.timeout)
        except httpx.HTTPError as e:
            raise HCUnavailable(f"celular não respondeu em {self.base_url}: {type(e).__name__}") from e
        if r.status_code == 401:
            raise HCUnavailable("token recusado pelo app (confira HC_TOKEN)")
        if r.status_code != 200:
            raise HCUnavailable(f"app respondeu {r.status_code}: {r.text[:200]}")
        try:
            return r.json()
        except ValueError as e:
            raise HCUnavailable("resposta do app não é JSON") from e

    def ping(self) -> bool:
        try:
            return self._get("/ping", timeout=5).get("status") == "ok"
        except HCUnavailable:
            return False

    def read(self, start: datetime, end: datetime) -> dict:
        fmt = lambda d: d.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        return self._get("/", params={"start": fmt(start), "end": fmt(end)})
