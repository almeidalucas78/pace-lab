"""Limite de tentativas de login erradas, em memória (um processo só no servidor).

Conta só as falhas, em janela deslizante. Limita por IP e por e-mail + IP; não bloqueia a conta para todo
mundo, para ninguém conseguir travar a conta de outra pessoa de propósito (ASVS 6.3.1). Reiniciar o servidor
zera os contadores, o que é aceitável: o Argon2 já deixa cada tentativa lenta.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

JANELA_S = 15 * 60
MAX_POR_IP = 20
MAX_POR_EMAIL_IP = 5


class Limite:
    def __init__(self) -> None:
        self._falhas: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _limpa(self, chave: str, agora: float) -> deque[float]:
        q = self._falhas[chave]
        while q and q[0] <= agora - JANELA_S:
            q.popleft()
        return q

    def espera(self, ip: str, email: str) -> int:
        """Segundos até poder tentar de novo (0 = pode tentar agora)."""
        agora = time.monotonic()
        with self._lock:
            esperas = []
            for chave, maximo in ((f"ip:{ip}", MAX_POR_IP), (f"em:{email}|{ip}", MAX_POR_EMAIL_IP)):
                q = self._limpa(chave, agora)
                if len(q) >= maximo:
                    esperas.append(int(q[0] + JANELA_S - agora) + 1)
            return max(esperas, default=0)

    def falhou(self, ip: str, email: str) -> None:
        agora = time.monotonic()
        with self._lock:
            self._falhas[f"ip:{ip}"].append(agora)
            self._falhas[f"em:{email}|{ip}"].append(agora)

    def acertou(self, ip: str, email: str) -> None:
        with self._lock:
            self._falhas.pop(f"em:{email}|{ip}", None)

    def zera(self) -> None:
        with self._lock:
            self._falhas.clear()


limite = Limite()
