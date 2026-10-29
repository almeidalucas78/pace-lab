"""API HTTP em /api e o painel web na raiz. Única porta de entrada para painel, chat e (no futuro) celular."""
from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from .. import services
from ..config import ROOT, Settings, get_settings
from ..db import session_scope
from ..ia.chat import conversar
from ..ia.provedores import ErroIA
from ..scheduler import SyncScheduler

# `treino servico` liga o agendador; `treino api` e os testes não.
SCHEDULER_ENV = "TREINO_AGENDADOR"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.scheduler = SyncScheduler(get_settings())
    if os.environ.get(SCHEDULER_ENV) == "1":
        app.state.scheduler.start()
    yield
    app.state.scheduler.stop()


app = FastAPI(title="Treino API", version="0.5.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
api = APIRouter(prefix="/api")
bearer = HTTPBearer(auto_error=False)


def auth(creds: HTTPAuthorizationCredentials | None = Depends(bearer),
         settings: Settings = Depends(get_settings)) -> Settings:
    if creds is None or not secrets.compare_digest(creds.credentials, settings.api_token):
        raise HTTPException(status_code=401, detail="token inválido")
    return settings


@api.get("/health")
def health():
    return {"status": "ok"}


@api.get("/overview")
def overview(settings: Settings = Depends(auth)):
    with session_scope() as s:
        return services.overview(s)


@api.get("/activities")
def activities(sport: str | None = None, limit: int = Query(20, le=200), offset: int = 0,
               settings: Settings = Depends(auth)):
    with session_scope() as s:
        return services.list_activities(s, settings, sport, limit, offset)


@api.get("/activities/{activity_id}")
def activity(activity_id: int, settings: Settings = Depends(auth)):
    with session_scope() as s:
        d = services.activity_detail(s, settings, activity_id)
        if d is not None:
            d["sensacoes"] = services.list_sensations(s, settings, activity_id=activity_id)
    if d is None:
        raise HTTPException(404, "treino não encontrado")
    return d


@api.get("/activities/{activity_id}/samples")
def samples(activity_id: int, every_s: float = Query(5, ge=1), settings: Settings = Depends(auth)):
    with session_scope() as s:
        return services.activity_samples(s, activity_id, every_s)


@api.get("/weeks")
def weeks(n: int = Query(12, le=104), sport: str = "run", settings: Settings = Depends(auth)):
    with session_scope() as s:
        return services.weekly_summary(s, settings, n, sport)


@api.get("/load")
def load(days: int = Query(90, le=3650), settings: Settings = Depends(auth)):
    with session_scope() as s:
        return services.load_series(s, days)


@api.get("/sync/status")
def sync_status(settings: Settings = Depends(auth)):
    with session_scope() as s:
        return services.sync_status(s, settings)


@api.post("/sync")
async def sync_now(request: Request, settings: Settings = Depends(auth)):
    if not settings.hc_url:
        raise HTTPException(400, "HC_URL não configurado no .env")
    return await run_in_threadpool(request.app.state.scheduler.run_now)


class ChatIn(BaseModel):
    mensagem: str = Field(min_length=1, max_length=20000)
    conversa_id: int | None = None
    provedor: str | None = Field(None, description="claude ou gemini; só vale ao começar conversa")
    contexto: str | None = Field(None, max_length=500, description="o que o usuário está vendo no painel")


@api.post("/chat")
async def chat(body: ChatIn, settings: Settings = Depends(auth)):
    try:
        return await conversar(body.mensagem, body.conversa_id, body.provedor, settings, contexto=body.contexto)
    except ErroIA as e:
        raise HTTPException(502, str(e))


@api.get("/chat/conversas")
def conversas(limit: int = Query(30, le=200), settings: Settings = Depends(auth)):
    with session_scope() as s:
        return services.list_conversations(s, settings, limit)


@api.get("/chat/conversas/{conversa_id}")
def conversa(conversa_id: int, settings: Settings = Depends(auth)):
    with session_scope() as s:
        d = services.conversation_detail(s, settings, conversa_id)
    if d is None:
        raise HTTPException(404, "conversa não encontrada")
    return d


@api.get("/sensacoes")
def sensacoes(dias: int = Query(30, le=3650), settings: Settings = Depends(auth)):
    with session_scope() as s:
        return services.list_sensations(s, settings, days=dias)


def _plano(fn):
    try:
        with session_scope() as s:
            return fn(s)
    except ValueError as e:
        raise HTTPException(404, str(e))


@api.get("/planos")
def planos(limit: int = Query(20, le=200), settings: Settings = Depends(auth)):
    with session_scope() as s:
        return services.list_plans(s, settings, limit)


@api.get("/planos/ativo")
def plano_ativo(settings: Settings = Depends(auth)):
    return _plano(lambda s: services.plan_dict(services.get_plan(s, None), settings))


@api.get("/planos/ativo/aderencia")
def aderencia_ativo(settings: Settings = Depends(auth)):
    return _plano(lambda s: services.plan_adherence(s, settings, None))


@api.get("/planos/{plano_id}")
def plano(plano_id: int, settings: Settings = Depends(auth)):
    return _plano(lambda s: services.plan_dict(services.get_plan(s, plano_id), settings))


@api.get("/planos/{plano_id}/aderencia")
def aderencia(plano_id: int, settings: Settings = Depends(auth)):
    return _plano(lambda s: services.plan_adherence(s, settings, plano_id))


@api.get("/perfil")
def perfil(settings: Settings = Depends(auth)):
    with session_scope() as s:
        return services.athlete_profile(s, settings)


@api.get("/carga/atual")
def carga_atual(settings: Settings = Depends(auth)):
    with session_scope() as s:
        return services.current_load(s, settings)


app.include_router(api)


# ---------- painel web (web/dist, gerado por `npm run build`) ----------

PAINEL = ROOT / "web" / "dist"


@app.get("/{caminho:path}", include_in_schema=False)
def painel(caminho: str):
    """Arquivos do painel; qualquer outra rota devolve o index.html (as rotas são do React Router)."""
    if caminho.startswith("api/") or caminho == "api":
        raise HTTPException(404, "rota da API não encontrada")
    if not (PAINEL / "index.html").exists():
        return JSONResponse({"aviso": "painel não compilado: rode `npm run build` na pasta web",
                             "api": "/api/docs"}, status_code=404)
    arquivo = (PAINEL / caminho).resolve()
    if caminho and arquivo.is_file() and PAINEL.resolve() in arquivo.parents:
        return FileResponse(arquivo)
    return FileResponse(PAINEL / "index.html", headers={"Cache-Control": "no-cache"})
