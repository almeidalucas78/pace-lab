"""De quem são os dados de cada chamada (fase 9, etapa 3; ADR 0018).

`Conta` leva o id do usuário e as preferências dele (FC máxima, FC de repouso, fuso) para o `services`, que filtra
tudo por ela. A API monta a conta a partir do login; o PC (comandos, MCP local, `API_TOKEN` na transição) usa a
primeira conta do banco, a do dono. As ferramentas da IA leem a conta do contexto, marcado por `usando`.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db.models import User


@dataclass(frozen=True)
class Conta:
    user_id: int
    fc_max: int | None
    fc_repouso: int | None
    timezone: str
    settings: Settings

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


class SemConta(Exception):
    """Nenhuma conta no banco: crie com `treino criar-usuario`."""


def da_conta(u: User, settings: Settings | None = None) -> Conta:
    return Conta(u.id, u.fc_max, u.fc_repouso, u.timezone or "America/Sao_Paulo", settings or get_settings())


def do_dono(s: Session, settings: Settings | None = None) -> Conta:
    """A primeira conta do banco: dona dos dados que existiam antes das contas."""
    u = s.scalar(select(User).order_by(User.id).limit(1))
    if u is None:
        raise SemConta("nenhuma conta no banco; crie com: treino criar-usuario seu@email")
    return da_conta(u, settings)


def do_usuario(s: Session, user_id: int, settings: Settings | None = None) -> Conta:
    u = s.get(User, user_id)
    if u is None:
        raise SemConta(f"conta {user_id} não existe")
    return da_conta(u, settings)


_atual: ContextVar[Conta | None] = ContextVar("conta_atual", default=None)


@contextmanager
def usando(conta: Conta) -> Iterator[Conta]:
    """Marca a conta das ferramentas da IA chamadas dentro do bloco."""
    token = _atual.set(conta)
    try:
        yield conta
    finally:
        _atual.reset(token)


def atual(s: Session) -> Conta:
    """Conta marcada por `usando`; fora dela (MCP local no PC), a do dono."""
    return _atual.get() or do_dono(s)
