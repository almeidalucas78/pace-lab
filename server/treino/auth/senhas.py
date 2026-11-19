"""Senhas: hash Argon2id (argon2-cffi, perfil RFC 9106 de pouca memória) e a regra mínima do ASVS 5.0 nível 1."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

MINIMO = 8  # ASVS 6.2.1
MAXIMO = 128  # sem limite baixo; só evita textos enormes no Argon2

_hasher = PasswordHasher()
# Hash de uma senha qualquer, para gastar o mesmo tempo quando o e-mail não existe.
_HASH_FALSO = _hasher.hash("senha-que-nao-existe-em-conta-nenhuma")


@lru_cache
def _comuns() -> frozenset[str]:
    arq = Path(__file__).with_name("senhas_comuns.txt")
    linhas = arq.read_text(encoding="utf-8").splitlines()
    return frozenset(x for x in linhas if x and not x.startswith("# "))


def problema(senha: str) -> str | None:
    """Motivo para recusar a senha nova, ou None se ela serve (ASVS 6.2.1 e 6.2.4)."""
    if len(senha) < MINIMO:
        return f"a senha precisa ter pelo menos {MINIMO} caracteres"
    if len(senha) > MAXIMO:
        return f"a senha pode ter no máximo {MAXIMO} caracteres"
    if senha.lower() in _comuns():
        return "essa senha está entre as mais usadas; escolha outra"
    return None


def gerar_hash(senha: str) -> str:
    return _hasher.hash(senha)


def confere(hash_guardado: str | None, senha: str) -> bool:
    """Confere a senha. Sem hash (conta só do Google ou e-mail inexistente), gasta o mesmo tempo e recusa."""
    try:
        return _hasher.verify(hash_guardado or _HASH_FALSO, senha) and hash_guardado is not None
    except (VerificationError, InvalidHashError):
        return False


def precisa_refazer(hash_guardado: str) -> bool:
    return _hasher.check_needs_rehash(hash_guardado)
