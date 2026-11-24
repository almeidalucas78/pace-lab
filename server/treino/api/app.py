"""API HTTP em /api e o painel web na raiz. Única porta de entrada para painel, chat e (no futuro) celular."""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import AwareDatetime, BaseModel, Field

from .. import services
from ..config import ROOT, Settings, get_settings
from ..conta import Conta, SemConta, da_conta, do_dono
from ..db import session_scope
from ..ia.chat import conversar
from ..ia.provedores import ErroIA
from ..notify import describe_new, notify
from . import auth as rotas_auth

app = FastAPI(
    title="Treino API", version="0.5.0", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None
)
api = APIRouter(prefix="/api")

# App Android (Capacitor, ADR 0013): o painel roda em https://localhost dentro do app e chama a API pelo
# endereço do Tailscale. Só essa origem é liberada; o painel no navegador usa o próprio site.
ORIGEM_APP = "https://localhost"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ORIGEM_APP],
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)
bearer = HTTPBearer(auto_error=False)


def logado(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> Settings:
    """Só confere o login, para rotas sem dados de usuário (APK do app, configuração do painel)."""
    rotas_auth.autenticar(request, creds, settings)
    return settings


def auth(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> Conta:
    """Conta de quem chama: a do login (cabeçalho ou cookie) ou, com o API_TOKEN antigo, aceito até as etapas
    7 e 8 (ADR 0017), a do dono. Toda rota de dados filtra por ela (ADR 0018)."""
    u = rotas_auth.autenticar(request, creds, settings)
    if u is not None:
        return da_conta(u, settings)
    try:
        with session_scope() as s:
            return do_dono(s, settings)
    except SemConta as e:
        raise HTTPException(503, str(e)) from e


@api.get("/health")
def health():
    return {"status": "ok"}


@api.get("/overview")
def overview(conta: Conta = Depends(auth)):
    with session_scope() as s:
        return services.overview(s, conta)


@api.get("/activities")
def activities(sport: str | None = None, limit: int = Query(20, le=200), offset: int = 0, conta: Conta = Depends(auth)):
    with session_scope() as s:
        return services.list_activities(s, conta, sport, limit, offset)


@api.get("/activities/{activity_id}")
def activity(activity_id: int, conta: Conta = Depends(auth)):
    with session_scope() as s:
        d = services.activity_detail(s, conta, activity_id)
        if d is not None:
            d["sensacoes"] = services.list_sensations(s, conta, activity_id=activity_id)
    if d is None:
        raise HTTPException(404, "treino não encontrado")
    return d


@api.get("/activities/{activity_id}/samples")
def samples(activity_id: int, every_s: float = Query(5, ge=1), conta: Conta = Depends(auth)):
    with session_scope() as s:
        amostras = services.activity_samples(s, conta, activity_id, every_s)
    if amostras is None:
        raise HTTPException(404, "treino não encontrado")
    return amostras


@api.get("/weeks")
def weeks(n: int = Query(12, le=104), sport: str = "run", conta: Conta = Depends(auth)):
    with session_scope() as s:
        return services.weekly_summary(s, conta, n, sport)


@api.get("/load")
def load(days: int = Query(90, le=3650), conta: Conta = Depends(auth)):
    with session_scope() as s:
        return services.load_series(s, conta, days)


@api.get("/sync/status")
def sync_status(conta: Conta = Depends(auth)):
    with session_scope() as s:
        return services.sync_status(s, conta)


class ChatIn(BaseModel):
    mensagem: str = Field(min_length=1, max_length=20000)
    conversa_id: int | None = None
    provedor: str | None = Field(None, description="claude ou gemini; só vale ao começar conversa")
    contexto: str | None = Field(None, max_length=500, description="o que o usuário está vendo no painel")


@api.post("/chat")
async def chat(body: ChatIn, conta: Conta = Depends(auth)):
    try:
        return await conversar(
            body.mensagem, body.conversa_id, body.provedor, conta.settings, contexto=body.contexto, conta=conta
        )
    except ErroIA as e:
        raise HTTPException(502, str(e)) from e


@api.get("/chat/conversas")
def conversas(limit: int = Query(30, le=200), conta: Conta = Depends(auth)):
    with session_scope() as s:
        return services.list_conversations(s, conta, limit)


@api.get("/chat/conversas/{conversa_id}")
def conversa(conversa_id: int, conta: Conta = Depends(auth)):
    with session_scope() as s:
        d = services.conversation_detail(s, conta, conversa_id)
    if d is None:
        raise HTTPException(404, "conversa não encontrada")
    return d


@api.get("/sensacoes")
def sensacoes(dias: int = Query(30, le=3650), conta: Conta = Depends(auth)):
    with session_scope() as s:
        return services.list_sensations(s, conta, days=dias)


def _plano(fn):
    try:
        with session_scope() as s:
            return fn(s)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e


@api.get("/planos")
def planos(limit: int = Query(20, le=200), conta: Conta = Depends(auth)):
    with session_scope() as s:
        return services.list_plans(s, conta, limit)


@api.get("/planos/ativo")
def plano_ativo(conta: Conta = Depends(auth)):
    return _plano(lambda s: services.plan_dict(services.get_plan(s, conta, None), conta))


@api.get("/planos/ativo/aderencia")
def aderencia_ativo(conta: Conta = Depends(auth)):
    return _plano(lambda s: services.plan_adherence(s, conta, None))


@api.get("/planos/{plano_id}")
def plano(plano_id: int, conta: Conta = Depends(auth)):
    return _plano(lambda s: services.plan_dict(services.get_plan(s, conta, plano_id), conta))


@api.get("/planos/{plano_id}/aderencia")
def aderencia(plano_id: int, conta: Conta = Depends(auth)):
    return _plano(lambda s: services.plan_adherence(s, conta, plano_id))


@api.get("/app/versao")
def app_versao(settings: Settings = Depends(logado)):
    """Versão do app Android publicada no PC; `codigo` nulo quando nada foi publicado."""
    return services.app_version(settings) or {"codigo": None}


@api.get("/app/apk")
def app_apk(settings: Settings = Depends(logado)):
    caminho = services.app_apk_path(settings)
    if caminho is None:
        raise HTTPException(status_code=404, detail="nenhuma versão do app publicada; rode treino publicar-app")
    return FileResponse(caminho, media_type="application/vnd.android.package-archive", filename=caminho.name)


@api.get("/perfil")
def perfil(conta: Conta = Depends(auth)):
    with session_scope() as s:
        return services.athlete_profile(s, conta)


class AjustesIn(BaseModel):
    fc_max: int | None = Field(None, ge=0, le=300, description="bpm; 0 = voltar a estimar pelos treinos")
    fc_repouso: int | None = Field(None, ge=0, le=300, description="bpm; 0 = apagar")
    fuso: str | None = Field(None, max_length=64, description="ex.: America/Sao_Paulo")


@api.post("/perfil/ajustes")
def ajustar_perfil(body: AjustesIn, conta: Conta = Depends(auth)):
    """FC máxima, FC de repouso e fuso da conta; recalcula zonas e carga e devolve o perfil novo."""
    try:
        with session_scope() as s:
            return services.ajustar_conta(s, conta, body.fc_max, body.fc_repouso, body.fuso)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e


@api.get("/carga/atual")
def carga_atual(conta: Conta = Depends(auth)):
    with session_scope() as s:
        return services.current_load(s, conta)


# ---------- treinos enviados pelo app Android (ADR 0013) ----------


class RegistroIn(BaseModel):
    t: int = Field(description="horário em ms desde 1970 (UTC)")
    fc: float | None = Field(None, ge=0, le=260)
    vel: float | None = Field(None, ge=0, le=30, description="m/s")
    cad: float | None = Field(None, ge=0, le=400, description="passos ou pedaladas por minuto")
    pot: float | None = Field(None, ge=0, le=3000, description="watts")


class PercursoIn(BaseModel):
    t: int
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    alt: float | None = Field(None, ge=-500, le=9000)


class TreinoIn(BaseModel):
    id: str = Field(min_length=1, max_length=64, description="id do treino na fonte (ex.: uid do Samsung Health)")
    tipo: str = Field(min_length=1, max_length=40, description="tipo na fonte, ex.: RUNNING")
    inicio: AwareDatetime
    fim: AwareDatetime
    duracao_s: float | None = Field(None, ge=0)
    distancia_m: float | None = Field(None, ge=0)
    calorias: float | None = Field(None, ge=0)
    fc_media: float | None = Field(None, ge=0, le=260)
    fc_max: float | None = Field(None, ge=0, le=260)
    cadencia_media: float | None = Field(None, ge=0, le=400)
    ganho_elevacao_m: float | None = Field(None, ge=0)
    vo2max: float | None = Field(None, ge=0, le=100)
    titulo: str | None = Field(None, max_length=200)
    registros: list[RegistroIn] = Field(default_factory=list, max_length=200_000)
    percurso: list[PercursoIn] = Field(default_factory=list, max_length=200_000)


class LoteTreinos(BaseModel):
    fonte: Literal["samsung_health", "health_connect"]
    treinos: list[TreinoIn] = Field(default_factory=list, max_length=50)
    apagados: list[str] = Field(default_factory=list, max_length=500, description="ids apagados na fonte")


@api.post("/saude/treinos")
def receber_treinos(lote: LoteTreinos, conta: Conta = Depends(auth)):
    for t in lote.treinos:
        if t.fim <= t.inicio:
            raise HTTPException(422, f"treino {t.id}: fim antes do início")
    with session_scope() as s:
        rep = services.receive_app_workouts(s, conta, lote.fonte, [t.model_dump() for t in lote.treinos], lote.apagados)
    msg = describe_new(rep["treinos_novos"])
    if msg:
        notify(*msg, enabled=conta.settings.notificacoes)
    return {k: v for k, v in rep.items() if k != "treinos_novos"} | {
        "novos_ids": [t["id"] for t in rep["treinos_novos"]]
    }


# ---------- export do Strava enviado pelo painel ----------

MAXIMO_EXPORT = 1024**3  # 1 GB; o export de anos de treino tem dezenas de MB
_importando: set[int] = set()  # uma importação por conta de cada vez


def _importar_strava(conta: Conta, caminho: Path) -> dict:
    try:
        with session_scope() as s:
            rep = services.importar_strava(s, conta, caminho)
    except (FileNotFoundError, zipfile.BadZipFile, ValueError) as e:
        raise HTTPException(400, f"não parece o export do Strava: {e}") from e
    rc = rep.pop("recalculo")
    return rep | {"fc_max": rc["fc_max"], "fc_max_origem": rc["fc_max_origem"]}


@api.post("/importar/strava")
async def importar_strava(request: Request, conta: Conta = Depends(auth)):
    """Recebe o .zip do export do Strava no corpo da requisição e importa na conta (rodar de novo só atualiza)."""
    tamanho = request.headers.get("content-length", "")
    if tamanho.isdigit() and int(tamanho) > MAXIMO_EXPORT:
        raise HTTPException(413, "arquivo grande demais (máximo 1 GB)")
    if conta.user_id in _importando:
        raise HTTPException(409, "já há uma importação em andamento")
    _importando.add(conta.user_id)
    try:
        with tempfile.TemporaryDirectory(prefix="pacelab-import-") as pasta:
            caminho = Path(pasta) / "export.zip"
            total = 0
            with caminho.open("wb") as f:
                async for parte in request.stream():
                    total += len(parte)
                    if total > MAXIMO_EXPORT:
                        raise HTTPException(413, "arquivo grande demais (máximo 1 GB)")
                    f.write(parte)
            if not zipfile.is_zipfile(caminho):
                raise HTTPException(400, "envie o arquivo .zip do export do Strava")
            return await run_in_threadpool(_importar_strava, conta, caminho)
    finally:
        _importando.discard(conta.user_id)


@api.get("/painel/config")
def painel_config(settings: Settings = Depends(logado)):
    return {"url_celular": settings.painel_url_celular.rstrip("/") or None}


api.include_router(rotas_auth.router)
app.include_router(api)


# ---------- painel web (web/dist, gerado por `npm run build`) ----------

PAINEL = ROOT / "web" / "dist"
TIPOS_PAINEL = {".webmanifest": "application/manifest+json", ".js": "text/javascript"}
SEM_CACHE = {"sw.js", "manifest.webmanifest", "registerSW.js"}


@app.get("/{caminho:path}", include_in_schema=False)
def painel(caminho: str):
    """Arquivos do painel; qualquer outra rota devolve o index.html (as rotas são do React Router)."""
    if caminho.startswith("api/") or caminho == "api":
        raise HTTPException(404, "rota da API não encontrada")
    if not (PAINEL / "index.html").exists():
        return JSONResponse(
            {"aviso": "painel não compilado: rode `npm run build` na pasta web", "api": "/api/docs"}, status_code=404
        )
    arquivo = (PAINEL / caminho).resolve()
    if caminho and arquivo.is_file() and PAINEL.resolve() in arquivo.parents:
        tipo = TIPOS_PAINEL.get(arquivo.suffix)
        # service worker e manifest sempre conferidos de novo, para o celular pegar versões novas do painel
        cache = {"Cache-Control": "no-cache"} if arquivo.name in SEM_CACHE else None
        return FileResponse(arquivo, media_type=tipo, headers=cache)
    return FileResponse(PAINEL / "index.html", headers={"Cache-Control": "no-cache"})
