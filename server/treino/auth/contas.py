"""Contas, sessões (tokens opacos guardados só como hash) e login com Google. Regras do ADR 0015 e do 0017."""

from __future__ import annotations

import base64
import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import Settings
from ..db import AuthPending, AuthSession, User
from . import senhas

GOOGLE_AUTORIZACAO = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
PENDENCIA_MIN = 10


class ErroConta(Exception):
    """Erro que pode ser mostrado ao usuário."""

    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.status = status


def agora() -> datetime:
    return datetime.now(UTC)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def normaliza_email(email: str) -> str:
    return email.strip().lower()


# ---------- contas ----------


def pode_cadastrar(settings: Settings, email: str) -> bool:
    """Cadastro fechado até a fase 12: só e-mails da lista CADASTRO_EMAILS."""
    return normaliza_email(email) in settings.emails_cadastro


def criar_usuario(
    s: Session, settings: Settings, email: str, senha: str | None, nome: str | None = None, *, livre: bool = False
) -> User:
    """Cria a conta. `livre` pula a lista de cadastro (comando `treino usuario criar`, feito por quem tem o PC)."""
    email = normaliza_email(email)
    if "@" not in email or len(email) > 254:
        raise ErroConta("e-mail inválido")
    if not livre and not pode_cadastrar(settings, email):
        raise ErroConta("cadastro fechado: este e-mail não está na lista de convidados", 403)
    if s.scalar(select(User.id).where(User.email == email)) is not None:
        raise ErroConta("já existe uma conta com este e-mail", 409)
    if senha is not None and (motivo := senhas.problema(senha)):
        raise ErroConta(motivo)
    u = User(
        email=email,
        name=(nome or "").strip()[:120] or None,
        password_hash=senhas.gerar_hash(senha) if senha is not None else None,
        created_utc=agora(),
    )
    s.add(u)
    s.flush()
    return u


CONTA_PROVISORIA = "dono@pacelab.local"  # criada pela migração 0006 quando havia dados e nenhuma conta


def assumir_provisoria(s: Session, email: str, senha: str | None, nome: str | None = None) -> User | None:
    """Se existe a conta provisória do dono, ela vira a conta de `email` (com os dados antigos). Senão, None."""
    u = s.scalar(select(User).where(User.email == CONTA_PROVISORIA))
    if u is None:
        return None
    email = normaliza_email(email)
    if "@" not in email or s.scalar(select(User.id).where(User.email == email)) is not None:
        raise ErroConta("e-mail inválido ou já usado por outra conta")
    if senha is not None and (motivo := senhas.problema(senha)):
        raise ErroConta(motivo)
    u.email, u.name = email, (nome or "").strip()[:120] or None
    u.password_hash = senhas.gerar_hash(senha) if senha is not None else None
    return u


def entrar_com_senha(s: Session, email: str, senha: str) -> User | None:
    """Usuário se o e-mail e a senha conferem; None em qualquer outro caso (mesmo tempo e mesma resposta)."""
    u = s.scalar(select(User).where(User.email == normaliza_email(email)))
    if not senhas.confere(u.password_hash if u else None, senha) or u is None:
        return None
    if u.password_hash and senhas.precisa_refazer(u.password_hash):
        u.password_hash = senhas.gerar_hash(senha)
    return u


def trocar_senha(s: Session, u: User, atual: str | None, nova: str, sessao_atual: int | None) -> None:
    """Troca a senha (pede a atual, se houver; ASVS 6.2.3) e derruba as outras sessões."""
    if u.password_hash and (atual is None or not senhas.confere(u.password_hash, atual)):
        raise ErroConta("senha atual errada", 403)
    if motivo := senhas.problema(nova):
        raise ErroConta(motivo)
    u.password_hash = senhas.gerar_hash(nova)
    revogar_todas(s, u.id, "senha", exceto=sessao_atual)


# ---------- sessões ----------


@dataclass
class Tokens:
    acesso: str
    renovacao: str
    acesso_expira: datetime
    renovacao_expira: datetime
    sessao_id: int


def _nova_linha(s: Session, settings: Settings, user_id: int, familia: str, aparelho: str | None) -> Tokens:
    acesso, renovacao = "pla_" + secrets.token_urlsafe(32), "plr_" + secrets.token_urlsafe(32)
    t = agora()
    linha = AuthSession(
        user_id=user_id,
        family=familia,
        access_hash=hash_token(acesso),
        access_expires_utc=t + timedelta(minutes=settings.acesso_minutos),
        refresh_hash=hash_token(renovacao),
        refresh_expires_utc=t + timedelta(days=settings.renovacao_dias),
        device=(aparelho or "")[:120] or None,
        created_utc=t,
    )
    s.add(linha)
    s.flush()
    return Tokens(acesso, renovacao, linha.access_expires_utc, linha.refresh_expires_utc, linha.id)


def criar_sessao(s: Session, settings: Settings, u: User, aparelho: str | None) -> Tokens:
    u.last_login_utc = agora()
    return _nova_linha(s, settings, u.id, secrets.token_hex(16), aparelho)


def usuario_do_acesso(s: Session, token: str) -> tuple[User, AuthSession] | None:
    linha = s.scalar(select(AuthSession).where(AuthSession.access_hash == hash_token(token)))
    if linha is None or linha.revoked_utc is not None or linha.access_expires_utc <= agora():
        return None
    u = s.get(User, linha.user_id)
    return (u, linha) if u else None


def renovar(s: Session, settings: Settings, token: str) -> Tokens | None:
    """Troca o token de renovação por um par novo. Token já trocado usado de novo = vazou: derruba a família."""
    linha = s.scalar(select(AuthSession).where(AuthSession.refresh_hash == hash_token(token)))
    if linha is None:
        return None
    if linha.revoked_utc is not None:
        if linha.revoked_reason == "renovada":
            _revogar_familia(s, linha.family, "reuso")
        return None
    if linha.refresh_expires_utc <= agora():
        return None
    linha.revoked_utc, linha.revoked_reason = agora(), "renovada"
    return _nova_linha(s, settings, linha.user_id, linha.family, linha.device)


def _revogar_familia(s: Session, familia: str, motivo: str) -> None:
    s.execute(
        update(AuthSession)
        .where(AuthSession.family == familia, AuthSession.revoked_utc.is_(None))
        .values(revoked_utc=agora(), revoked_reason=motivo)
    )


def sair(s: Session, linha: AuthSession) -> None:
    _revogar_familia(s, linha.family, "saiu")


def revogar_todas(s: Session, user_id: int, motivo: str = "sair_todos", exceto: int | None = None) -> None:
    familia_mantida = s.scalar(select(AuthSession.family).where(AuthSession.id == exceto)) if exceto else None
    q = update(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_utc.is_(None))
    if familia_mantida:
        q = q.where(AuthSession.family != familia_mantida)
    s.execute(q.values(revoked_utc=agora(), revoked_reason=motivo))


def usuario_dict(u: User) -> dict[str, Any]:
    return {
        "id": u.id,
        "email": u.email,
        "nome": u.name,
        "google": u.google_sub is not None,
        "senha": bool(u.password_hash),
    }


# ---------- login com Google (fluxo de código no servidor, com state, nonce e PKCE) ----------


def url_retorno_google(settings: Settings) -> str:
    return settings.url_publica.rstrip("/") + "/api/auth/google/retorno"


def iniciar_google(s: Session, settings: Settings, destino: str) -> tuple[str, str]:
    """URL do Google para onde mandar o navegador e o vínculo que vai num cookie (prende o login a este navegador)."""
    state, nonce, verificador, vinculo = (secrets.token_urlsafe(32) for _ in range(4))
    desafio = desafio_pkce(verificador)
    s.add(
        AuthPending(
            kind="google",
            key_hash=hash_token(state),
            data={"nonce": nonce, "verificador": verificador, "destino": destino, "vinculo": hash_token(vinculo)},
            expires_utc=agora() + timedelta(minutes=PENDENCIA_MIN),
        )
    )
    params = {
        "client_id": settings.google_client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": url_retorno_google(settings),
        "state": state,
        "nonce": nonce,
        "code_challenge": desafio,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTORIZACAO}?{urlencode(params)}", vinculo


def pegar_pendencia_google(s: Session, state: str, vinculo: str | None) -> dict[str, Any]:
    p = s.scalar(select(AuthPending).where(AuthPending.kind == "google", AuthPending.key_hash == hash_token(state)))
    if p is None or p.used_utc is not None or p.expires_utc <= agora():
        raise ErroConta("login com Google expirado; tente de novo")
    if not vinculo or not secrets.compare_digest(p.data["vinculo"], hash_token(vinculo)):
        raise ErroConta("login com Google começou em outro navegador; tente de novo")
    p.used_utc = agora()
    return dict(p.data)


def usuario_do_google(s: Session, settings: Settings, dados: dict[str, Any]) -> User:
    """Acha ou cria a conta a partir do id_token já conferido. A chave é o `sub` (o e-mail pode mudar)."""
    sub = str(dados["sub"])
    u = s.scalar(select(User).where(User.google_sub == sub))
    if u is not None:
        return u
    email = normaliza_email(str(dados.get("email", "")))
    if not email or dados.get("email_verified") is not True:
        raise ErroConta("a conta Google precisa ter e-mail confirmado", 403)
    u = s.scalar(select(User).where(User.email == email))
    if u is not None:
        u.google_sub = sub  # mesma pessoa: e-mail confirmado pelo Google igual ao da conta
        return u
    u = criar_usuario(s, settings, email, None, str(dados.get("name") or ""))
    u.google_sub = sub
    return u


def trocar_codigo_google(settings: Settings, codigo: str, verificador: str, nonce: str) -> dict[str, Any]:
    """Troca o código pelo id_token e confere assinatura, emissor, público e validade (google-auth) e o nonce."""
    import httpx
    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport.requests import Request
    from google.oauth2 import id_token

    r = httpx.post(
        GOOGLE_TOKEN,
        data={
            "code": codigo,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": url_retorno_google(settings),
            "grant_type": "authorization_code",
            "code_verifier": verificador,
        },
        timeout=15,
    )
    if r.status_code != 200 or "id_token" not in r.json():
        raise ErroConta("o Google recusou o login; tente de novo", 502)
    try:
        dados: dict[str, Any] = dict(
            id_token.verify_oauth2_token(r.json()["id_token"], Request(), settings.google_client_id, 10)
        )
    except (ValueError, GoogleAuthError) as e:
        raise ErroConta("resposta do Google inválida", 502) from e
    if not secrets.compare_digest(str(dados.get("nonce", "")), nonce):
        raise ErroConta("resposta do Google inválida", 502)
    return dados


# ---------- login do app Android pelo navegador (ADR 0015): código de uso único com PKCE ----------


def desafio_pkce(verificador: str) -> str:
    """S256 do PKCE (RFC 7636): base64url sem "=" do SHA-256 do verificador."""
    return base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).rstrip(b"=").decode()


def criar_codigo_app(s: Session, user_id: int, desafio: str) -> str:
    """Quem já entrou no navegador gera um código que só o app que criou o desafio consegue trocar por tokens."""
    codigo = secrets.token_urlsafe(32)
    s.add(
        AuthPending(
            kind="app",
            key_hash=hash_token(codigo),
            data={"user_id": user_id, "desafio": desafio},
            expires_utc=agora() + timedelta(minutes=PENDENCIA_MIN),
        )
    )
    return codigo


def usar_codigo_app(s: Session, codigo: str, verificador: str) -> User | None:
    """Dono do código, se ele vale e o verificador confere. Uso único: errar o verificador também gasta o código."""
    p = s.scalar(select(AuthPending).where(AuthPending.kind == "app", AuthPending.key_hash == hash_token(codigo)))
    if p is None or p.used_utc is not None or p.expires_utc <= agora():
        return None
    p.used_utc = agora()
    if not secrets.compare_digest(desafio_pkce(verificador), str(p.data["desafio"])):
        return None
    return s.get(User, int(p.data["user_id"]))
