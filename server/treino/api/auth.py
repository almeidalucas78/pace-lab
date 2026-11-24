"""Rotas de conta e login em /api/auth (fase 9, ADRs 0015 e 0017).

Painel no navegador: tokens em cookies HttpOnly, Secure e SameSite=Strict (JavaScript não lê). App e programas:
tokens no corpo da resposta e no cabeçalho Authorization. O token de renovação só vai para /api/auth/renovar.
"""

from __future__ import annotations

import secrets
from typing import Literal

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from ..auth import contas
from ..auth.limite import limite
from ..config import Settings, get_settings
from ..db import session_scope
from ..db.models import AuthSession, User

COOKIE_ACESSO = "pl_acesso"
COOKIE_RENOVACAO = "pl_renovacao"
COOKIE_GOOGLE = "pl_google"
METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}

router = APIRouter(prefix="/auth")
bearer = HTTPBearer(auto_error=False)


# ---------- quem está chamando ----------


def _origem_confiavel(request: Request) -> bool:
    """Contra CSRF: chamada que grava com cookie precisa vir do próprio site (ou do app)."""
    origem = request.headers.get("origin")
    if origem is None:
        ref = request.headers.get("referer", "")
        origem = "/".join(ref.split("/")[:3]) if ref else None
    if origem is None:
        return False
    proprio = f"{request.url.scheme}://{request.url.netloc}"
    return origem in {proprio, "https://localhost"}


def autenticar(request: Request, creds: HTTPAuthorizationCredentials | None, settings: Settings) -> User | None:
    """Usuário dono do token (cabeçalho ou cookie). Devolve None para o API_TOKEN antigo (até as etapas 7 e 8)."""
    token = creds.credentials if creds else request.cookies.get(COOKIE_ACESSO)
    if not token:
        raise HTTPException(401, "faça login")
    if creds and not token.startswith("pla_"):
        if secrets.compare_digest(token, settings.api_token):
            return None
        raise HTTPException(401, "token inválido")
    if creds is None and request.method not in METODOS_SEGUROS and not _origem_confiavel(request):
        raise HTTPException(403, "origem não permitida")
    with session_scope() as s:
        achado = contas.usuario_do_acesso(s, token)
        if achado is None:
            raise HTTPException(401, "sessão expirada; faça login de novo")
        u, linha = achado
        request.state.sessao_id = linha.id
        return u


def usuario_atual(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> User:
    u = autenticar(request, creds, settings)
    if u is None:
        raise HTTPException(401, "esta rota pede login de usuário")
    return u


def _ip(request: Request) -> str:
    return request.client.host if request.client else "?"


# ---------- respostas com tokens ----------


def _entregar(resp: Response, settings: Settings, t: contas.Tokens, cliente: str) -> dict:
    if cliente == "app":
        return {
            "acesso": t.acesso,
            "renovacao": t.renovacao,
            "acesso_expira": t.acesso_expira.isoformat(),
            "renovacao_expira": t.renovacao_expira.isoformat(),
        }
    for nome, valor, idade, caminho in (
        (COOKIE_ACESSO, t.acesso, settings.acesso_minutos * 60, "/api"),
        (COOKIE_RENOVACAO, t.renovacao, settings.renovacao_dias * 86400, "/api/auth/renovar"),
    ):
        resp.set_cookie(
            nome, valor, max_age=idade, path=caminho, httponly=True, secure=settings.cookie_seguro, samesite="strict"
        )
    return {"acesso_expira": t.acesso_expira.isoformat()}


def _apagar_cookies(resp: Response) -> None:
    resp.delete_cookie(COOKIE_ACESSO, path="/api")
    resp.delete_cookie(COOKIE_RENOVACAO, path="/api/auth/renovar")


def _erro(e: contas.ErroConta) -> HTTPException:
    return HTTPException(e.status, str(e))


@router.get("/opcoes")
def opcoes(settings: Settings = Depends(get_settings)):
    """Público: o que a tela de entrar mostra."""
    return {"google": settings.google_ligado}


# ---------- senha ----------


class CadastroIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    senha: str = Field(min_length=1, max_length=1000)
    nome: str | None = Field(None, max_length=120)
    cliente: Literal["web", "app"] = "web"


class EntrarIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    senha: str = Field(min_length=1, max_length=1000)
    cliente: Literal["web", "app"] = "web"


@router.post("/cadastro", status_code=201)
def cadastro(body: CadastroIn, request: Request, response: Response, settings: Settings = Depends(get_settings)):
    try:
        with session_scope() as s:
            u = contas.criar_usuario(s, settings, body.email, body.senha, body.nome)
            t = contas.criar_sessao(s, settings, u, body.cliente)
            return {"usuario": contas.usuario_dict(u)} | _entregar(response, settings, t, body.cliente)
    except contas.ErroConta as e:
        raise _erro(e) from e


@router.post("/entrar")
def entrar(body: EntrarIn, request: Request, response: Response, settings: Settings = Depends(get_settings)):
    ip, email = _ip(request), contas.normaliza_email(body.email)
    if espera := limite.espera(ip, email):
        raise HTTPException(
            429, f"muitas tentativas; tente de novo em {espera // 60 + 1} min", {"Retry-After": str(espera)}
        )
    with session_scope() as s:
        u = contas.entrar_com_senha(s, email, body.senha)
        if u is None:
            limite.falhou(ip, email)
            raise HTTPException(401, "e-mail ou senha errados")
        limite.acertou(ip, email)
        t = contas.criar_sessao(s, settings, u, body.cliente)
        return {"usuario": contas.usuario_dict(u)} | _entregar(response, settings, t, body.cliente)


class RenovarIn(BaseModel):
    renovacao: str | None = Field(None, max_length=200)


@router.post("/renovar")
def renovar(
    request: Request,
    response: Response,
    body: RenovarIn | None = None,
    pl_renovacao: str | None = Cookie(None),
    settings: Settings = Depends(get_settings),
):
    cliente = "app" if body and body.renovacao else "web"
    token = body.renovacao if body and body.renovacao else pl_renovacao
    if cliente == "web" and not _origem_confiavel(request):
        raise HTTPException(403, "origem não permitida")
    if not token:
        raise HTTPException(401, "faça login")
    with session_scope() as s:
        t = contas.renovar(s, settings, token)
    if t is None:
        resp = JSONResponse({"detail": "sessão expirada; faça login de novo"}, status_code=401)
        _apagar_cookies(resp)
        return resp
    return _entregar(response, settings, t, cliente)


@router.post("/sair")
def sair(request: Request, response: Response, u: User = Depends(usuario_atual)):
    with session_scope() as s:
        linha = s.get(AuthSession, request.state.sessao_id)
        if linha:
            contas.sair(s, linha)
    _apagar_cookies(response)
    return {"ok": True}


@router.post("/sair-de-todos")
def sair_de_todos(response: Response, u: User = Depends(usuario_atual)):
    with session_scope() as s:
        contas.revogar_todas(s, u.id)
    _apagar_cookies(response)
    return {"ok": True}


@router.get("/eu")
def eu(u: User = Depends(usuario_atual)):
    return contas.usuario_dict(u)


class TrocarSenhaIn(BaseModel):
    atual: str | None = Field(None, max_length=1000)
    nova: str = Field(min_length=1, max_length=1000)


@router.post("/trocar-senha")
def trocar_senha(body: TrocarSenhaIn, request: Request, u: User = Depends(usuario_atual)):
    try:
        with session_scope() as s:
            conta = s.get(User, u.id)
            assert conta is not None
            contas.trocar_senha(s, conta, body.atual, body.nova, request.state.sessao_id)
    except contas.ErroConta as e:
        raise _erro(e) from e
    return {"ok": True}


# ---------- Google ----------


@router.get("/google/iniciar")
def google_iniciar(settings: Settings = Depends(get_settings)):
    if not settings.google_ligado:
        raise HTTPException(404, "login com Google não configurado")
    with session_scope() as s:
        url, vinculo = contas.iniciar_google(s, settings, "web")
    resp = RedirectResponse(url, status_code=302)
    # Lax: precisa voltar no redirecionamento vindo do Google (navegação de outro site).
    resp.set_cookie(
        COOKIE_GOOGLE,
        vinculo,
        max_age=contas.PENDENCIA_MIN * 60,
        path="/api/auth/google",
        httponly=True,
        secure=settings.cookie_seguro,
        samesite="lax",
    )
    return resp


@router.get("/google/retorno")
def google_retorno(
    state: str = "",
    code: str = "",
    error: str = "",
    pl_google: str | None = Cookie(None),
    settings: Settings = Depends(get_settings),
):
    destino_erro = "/?erro_login="
    if error or not state or not code:
        return RedirectResponse(destino_erro + "google_cancelado", status_code=302)
    try:
        with session_scope() as s:
            p = contas.pegar_pendencia_google(s, state, pl_google)
        dados = contas.trocar_codigo_google(settings, code, p["verificador"], p["nonce"])
        with session_scope() as s:
            u = contas.usuario_do_google(s, settings, dados)
            t = contas.criar_sessao(s, settings, u, "web")
    except contas.ErroConta as e:
        motivo = "google_sem_convite" if e.status == 403 else "google_falhou"
        return RedirectResponse(destino_erro + motivo, status_code=302)
    resp = RedirectResponse("/", status_code=302)
    _entregar(resp, settings, t, "web")
    resp.delete_cookie(COOKIE_GOOGLE, path="/api/auth/google")
    return resp
