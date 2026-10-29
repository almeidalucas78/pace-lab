"""Regras de negócio e consultas. CLI, API, agendador, MCP e chat chamam só daqui."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session, selectinload

from .config import Settings
from .core.load import (ENDURANCE_SPORTS, ZONES, daily_series, estimate_fc_max, trimp_from_average,
                        trimp_from_zones, zones_from_samples)
from .db.models import Activity, ChatMessage, Conversation, DailyLoad, Sample, Sensation, Split, SyncState
from .ingest.hc_client import HCUnavailable
from .ingest.hc_import import import_payload
from .ingest.health_connect import parse_payload

DUPLICATE_WINDOW = timedelta(minutes=10)
SOURCE_PRIORITY = {"strava": 0, "health_connect": 1}  # menor vence quando o mesmo treino vem das duas fontes


# ---------- recálculo ----------

def mark_duplicates(session: Session) -> int:
    """Agrupa treinos do mesmo esporte que começam até 10 min depois do primeiro do grupo.
    Fica valendo o de fonte mais confiável (Strava antes do Health Connect); empate, o mais cedo."""
    acts = session.scalars(select(Activity).order_by(Activity.start_utc, Activity.id)).all()
    groups: list[list[Activity]] = []
    open_group: dict[str, list[Activity]] = {}
    for a in acts:
        a.possible_duplicate_of = None
        g = open_group.get(a.sport)
        if g and a.start_utc - g[0].start_utc <= DUPLICATE_WINDOW:
            g.append(a)
        else:
            open_group[a.sport] = [a]
            groups.append(open_group[a.sport])
    count = 0
    for g in groups:
        keeper = min(g, key=lambda a: SOURCE_PRIORITY.get(a.source, 99))  # min é estável: empate fica o mais cedo
        for a in g:
            if a is not keeper:
                a.possible_duplicate_of = keeper.id
                count += 1
    return count


def resolve_fc_max(session: Session, settings: Settings) -> tuple[float | None, str]:
    if settings.fc_max:
        return float(settings.fc_max), "configurada"
    vals = []
    for a in session.scalars(select(Activity).where(Activity.hr_quality == "ok")):
        v = (a.extra or {}).get("fc_30s_max")
        if v:
            vals.append(v)
    est = estimate_fc_max(vals)
    return (float(est), "estimada") if est else (None, "indisponivel")


def recompute(session: Session, settings: Settings) -> dict:
    dups = mark_duplicates(session)
    fc_max, fc_src = resolve_fc_max(session, settings)
    tz = settings.tz
    trimp_by_day: dict[date, float] = defaultdict(float)
    methods = defaultdict(int)

    acts = session.scalars(select(Activity).options(selectinload(Activity.samples))).all()
    for a in acts:
        a.hr_zones_s = a.trimp = a.trimp_method = None
        if fc_max:
            if a.samples and a.hr_quality in ("ok", "suspeita", "suspeita_cadencia"):
                a.hr_zones_s = zones_from_samples(a.samples, fc_max)
                a.trimp, a.trimp_method = trimp_from_zones(a.hr_zones_s), "streams"
            elif a.avg_hr and a.moving_s:
                a.trimp, a.trimp_method = trimp_from_average(a.avg_hr, a.moving_s, fc_max), "media"
        methods[a.trimp_method or "sem_carga"] += 1
        if a.trimp and a.sport in ENDURANCE_SPORTS and a.possible_duplicate_of is None:
            trimp_by_day[a.start_utc.astimezone(tz).date()] += a.trimp

    session.execute(delete(DailyLoad))
    today = datetime.now(tz).date()
    series = daily_series(dict(trimp_by_day), end=today)
    if series:
        session.execute(insert(DailyLoad), [d.__dict__ for d in series])
    return {"duplicatas": dups, "fc_max": fc_max, "fc_max_origem": fc_src,
            "carga_por_metodo": dict(methods), "dias": len(series)}


# ---------- consultas ----------

def _local(dt: datetime, settings: Settings) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(settings.tz).isoformat(timespec="minutes")


def pace_str(seconds_per_km: float | None) -> str | None:
    if not seconds_per_km:
        return None
    m, s = divmod(round(seconds_per_km), 60)
    return f"{m}:{s:02d}/km"


def activity_summary(a: Activity, settings: Settings) -> dict:
    pace = (a.moving_s / (a.distance_m / 1000)) if a.moving_s and a.distance_m else None
    return {
        "id": a.id, "data": _local(a.start_utc, settings), "esporte": a.sport, "tipo_original": a.sport_raw,
        "nome": a.name, "distancia_km": round(a.distance_m / 1000, 2) if a.distance_m else None,
        "tempo_movimento_min": round(a.moving_s / 60, 1) if a.moving_s else None,
        "ritmo": pace_str(pace) if a.sport in ("run", "walk") else None,
        "fc_media": a.avg_hr, "fc_max": a.max_hr, "cadencia_ppm": a.avg_cadence_spm,
        "ganho_elevacao_m": a.elev_gain_m, "temperatura_c": a.temp_c,
        "umidade_pct": round(a.humidity * 100) if a.humidity is not None else None,
        "tenis": a.gear, "carga": a.trimp, "qualidade_fc": a.hr_quality,
        "possivel_duplicata_de": a.possible_duplicate_of, "arquivo": a.file_status,
    }


def list_activities(session: Session, settings: Settings, sport: str | None = None,
                    limit: int = 20, offset: int = 0, since: date | None = None,
                    include_duplicates: bool = True) -> list[dict]:
    q = select(Activity).order_by(Activity.start_utc.desc()).limit(limit).offset(offset)
    if sport:
        q = q.where(Activity.sport == sport)
    if since:
        q = q.where(Activity.start_utc >= datetime.combine(since, datetime.min.time(), tzinfo=settings.tz))
    if not include_duplicates:
        q = q.where(Activity.possible_duplicate_of.is_(None))
    return [activity_summary(a, settings) for a in session.scalars(q)]


def activity_detail(session: Session, settings: Settings, activity_id: int) -> dict | None:
    a = session.get(Activity, activity_id)
    if a is None:
        return None
    out = activity_summary(a, settings)
    out["descricao"] = a.description
    out["percepcao_esforco"] = a.rpe
    out["zonas_fc_min"] = {k: round(v / 60, 1) for k, v in (a.hr_zones_s or {}).items()} or None
    out["parciais"] = [
        {"km": s.km, "distancia_m": round(s.distance_m), "ritmo": pace_str(s.pace_s_km),
         "fc_media": round(s.avg_hr) if s.avg_hr else None,
         "elevacao_m": round(s.elev_delta_m, 1) if s.elev_delta_m is not None else None}
        for s in a.splits
    ]
    extra = a.extra or {}
    out["observacoes_dados"] = {k: v for k, v in extra.items() if k != "detalhe_bruto"}
    return out


def activity_samples(session: Session, activity_id: int, every_s: float = 5) -> list[dict]:
    rows = session.scalars(select(Sample).where(Sample.activity_id == activity_id).order_by(Sample.t_s)).all()
    out, last = [], None
    for s in rows:
        if last is None or s.t_s - last >= every_s:
            out.append({"t": s.t_s, "lat": s.lat, "lon": s.lon, "ele": s.ele_m, "fc": s.hr,
                        "cad": s.cadence_spm, "vel": s.speed_ms, "dist": s.dist_m})
            last = s.t_s
    return out


def weekly_summary(session: Session, settings: Settings, weeks: int = 12, sport: str = "run") -> list[dict]:
    tz = settings.tz
    today = datetime.now(tz).date()
    start_week = today - timedelta(days=today.weekday()) - timedelta(weeks=weeks - 1)
    since = datetime.combine(start_week, datetime.min.time(), tzinfo=tz)
    acts = session.scalars(select(Activity).where(
        Activity.sport == sport, Activity.start_utc >= since, Activity.possible_duplicate_of.is_(None))).all()
    buckets = {start_week + timedelta(weeks=i): {"treinos": 0, "km": 0.0, "min": 0.0, "carga": 0.0, "longao_km": 0.0}
               for i in range(weeks)}
    for a in acts:
        d = a.start_utc.astimezone(tz).date()
        wk = d - timedelta(days=d.weekday())
        b = buckets.get(wk)
        if b is None:
            continue
        km = (a.distance_m or 0) / 1000
        b["treinos"] += 1
        b["km"] += km
        b["min"] += (a.moving_s or 0) / 60
        b["carga"] += a.trimp or 0
        b["longao_km"] = max(b["longao_km"], km)
    out = []
    for wk, b in buckets.items():
        pace = (b["min"] * 60 / b["km"]) if b["km"] else None
        out.append({"semana": wk.isoformat(), "treinos": b["treinos"], "km": round(b["km"], 1),
                    "tempo_min": round(b["min"]), "ritmo_medio": pace_str(pace),
                    "maior_treino_km": round(b["longao_km"], 1), "carga": round(b["carga"])})
    return out


def load_series(session: Session, days: int = 90) -> list[dict]:
    rows = session.scalars(select(DailyLoad).order_by(DailyLoad.day.desc()).limit(days)).all()
    return [{"dia": r.day.isoformat(), "carga": r.trimp, "fitness": r.fitness, "fadiga": r.fatigue, "forma": r.form}
            for r in reversed(rows)]


def overview(session: Session) -> dict:
    by_sport = dict(session.execute(select(Activity.sport, func.count()).group_by(Activity.sport)).all())
    first, last = session.execute(select(func.min(Activity.start_utc), func.max(Activity.start_utc))).one()
    files = dict(session.execute(select(Activity.file_status, func.count()).group_by(Activity.file_status)).all())
    return {"por_esporte": by_sport, "primeira": first.isoformat() if first else None,
            "ultima": last.isoformat() if last else None, "arquivos": files}


# ---------- sincronização com o Health Connect ----------

HC_SOURCE = "health_connect"


def sync_status(session: Session, settings: Settings) -> dict:
    st = session.get(SyncState, HC_SOURCE)
    return {
        "fonte": HC_SOURCE, "configurada": bool(settings.hc_url),
        "ultimo_sucesso": _local(st.last_success_utc, settings) if st and st.last_success_utc else None,
        "ultima_tentativa": _local(st.last_attempt_utc, settings) if st and st.last_attempt_utc else None,
        "ultimo_erro": st.last_error if st else None,
        "ultimo_resultado": st.last_result if st else None,
    }


def sync_health_connect(session: Session, settings: Settings, client, now: datetime | None = None) -> dict:
    """Lê do celular tudo desde a última leitura bem-sucedida (menos a margem), grava, deduplica e recalcula.
    `client` precisa ter read(start, end) -> dict e levantar HCUnavailable quando o celular não responde."""
    now = now or datetime.now(timezone.utc)
    st = session.get(SyncState, HC_SOURCE)
    if st is None:
        st = SyncState(source=HC_SOURCE)
        session.add(st)
    if st.last_success_utc:
        start = st.last_success_utc - timedelta(hours=settings.sync_margem_h)
    else:
        start = now - timedelta(days=settings.sync_primeira_janela_dias)
    st.last_attempt_utc = now
    try:
        raw = client.read(start, now)
    except HCUnavailable as e:
        st.last_error = str(e)
        return {"status": "indisponivel", "erro": str(e), "novos": []}

    rep = import_payload(session, parse_payload(raw))
    rc = recompute(session, settings)
    novos = [activity_summary(a, settings) for a in
             session.scalars(select(Activity).where(Activity.id.in_(rep["novas_ids"]),
                                                    Activity.possible_duplicate_of.is_(None))
                             .order_by(Activity.start_utc))]
    result = {"status": "ok", "janela": [_local(start, settings), _local(now, settings)],
              "sessoes_lidas": len(raw.get("exercise") or []), "novas": len(rep["novas_ids"]),
              "novas_duplicadas": len(rep["novas_ids"]) - len(novos), "atualizadas": rep["atualizadas"],
              "apagadas": rep["apagadas"], "fc_max": rc["fc_max"], "fc_max_origem": rc["fc_max_origem"]}
    st.last_success_utc, st.last_error, st.last_result = now, None, result
    return {**result, "novos": novos}


# ---------- fichas para a IA (resumidas, sem dados brutos) ----------

def last_activity_id(session: Session, sport: str | None = "run") -> int | None:
    q = select(Activity.id).where(Activity.possible_duplicate_of.is_(None)).order_by(Activity.start_utc.desc()).limit(1)
    if sport:
        q = q.where(Activity.sport == sport)
    return session.scalar(q)


def activity_card(session: Session, settings: Settings, activity_id: int) -> dict | None:
    """Detalhe do treino sem as notas técnicas de importação, com as sensações registradas."""
    d = activity_detail(session, settings, activity_id)
    if d is None:
        return None
    obs = d.pop("observacoes_dados", {}) or {}
    d["fc_colada_cadencia_pct"] = obs.get("fc_colada_cadencia_pct")
    d["fonte"] = session.get(Activity, activity_id).source
    for k in [k for k, v in d.items() if v is None]:
        del d[k]
    d["sensacoes"] = list_sensations(session, settings, activity_id=activity_id)
    return d


def current_load(session: Session, settings: Settings) -> dict:
    """Fitness, fadiga e forma de hoje, comparados com 7 e 28 dias atrás, e a carga dos últimos 14 dias."""
    rows = load_series(session, days=29)
    if not rows:
        return {"aviso": "sem dados de carga"}
    today = rows[-1]
    fc_max, origem = resolve_fc_max(session, settings)

    def at(n):
        return rows[-1 - n] if len(rows) > n else None

    return {
        "hoje": today,
        "ha_7_dias": at(7), "ha_28_dias": at(28),
        "carga_ultimos_14_dias": [{"dia": r["dia"], "carga": r["carga"]} for r in rows[-14:] if r["carga"]],
        "carga_7_dias": round(sum(r["carga"] for r in rows[-7:]), 1),
        "fc_max_usada": fc_max, "fc_max_origem": origem,
        "como_ler": "carga = TRIMP de Edwards (minutos em cada zona x peso 1 a 5); fitness = média exponencial "
                    "de 42 dias; fadiga = 7 dias; forma = fitness menos fadiga ao acordar. Só corrida, caminhada "
                    "e pedalada entram.",
    }


def athlete_profile(session: Session, settings: Settings) -> dict:
    fc_max, origem = resolve_fc_max(session, settings)
    zones = None
    if fc_max:
        bounds = [lo for _, lo in ZONES] + [None]
        zones = {z: f"{round(lo * fc_max)} a {round(bounds[i + 1] * fc_max) - 1 if bounds[i + 1] else round(fc_max)} bpm"
                 for i, (z, lo) in enumerate(ZONES)}
    return {
        "fc_max": fc_max, "fc_max_origem": origem,
        "fc_max_observacao": ("ESTIMATIVA: maior média de 30 s nos treinos com FC confiável; não é medida em teste"
                              if origem == "estimada" else None),
        "fc_repouso": settings.fc_repouso,
        "zonas_fc": zones,
        "historico": overview(session),
        "fuso": settings.timezone,
    }


# ---------- sensações ----------

def add_sensation(session: Session, settings: Settings, text: str, rpe: float | None = None,
                  activity_id: int | None = None, day: date | None = None, tags: list[str] | None = None) -> dict:
    if activity_id is not None:
        a = session.get(Activity, activity_id)
        if a is None:
            raise ValueError(f"treino {activity_id} não existe")
        day = day or a.start_utc.astimezone(settings.tz).date()
    if rpe is not None and not 1 <= rpe <= 10:
        raise ValueError("percepção de esforço vai de 1 a 10")
    s = Sensation(created_utc=datetime.now(timezone.utc), day=day or datetime.now(settings.tz).date(),
                  activity_id=activity_id, rpe=rpe, text=text.strip(), tags=tags or None)
    session.add(s)
    session.flush()
    return _sensation_dict(s)


def _sensation_dict(s: Sensation) -> dict:
    return {"id": s.id, "dia": s.day.isoformat(), "treino_id": s.activity_id, "rpe": s.rpe,
            "texto": s.text, "tags": s.tags}


def list_sensations(session: Session, settings: Settings, days: int | None = None,
                    activity_id: int | None = None) -> list[dict]:
    q = select(Sensation).order_by(Sensation.day.desc(), Sensation.id.desc())
    if activity_id is not None:
        q = q.where(Sensation.activity_id == activity_id)
    if days is not None:
        q = q.where(Sensation.day >= datetime.now(settings.tz).date() - timedelta(days=days))
    return [_sensation_dict(s) for s in session.scalars(q)]


# ---------- conversas do chat ----------

def create_conversation(session: Session, provider: str, title: str | None = None) -> Conversation:
    now = datetime.now(timezone.utc)
    c = Conversation(created_utc=now, updated_utc=now, provider=provider, title=(title or "")[:200] or None)
    session.add(c)
    session.flush()
    return c


def add_chat_message(session: Session, conversation: Conversation, role: str, content: str,
                     meta: dict | None = None) -> ChatMessage:
    now = datetime.now(timezone.utc)
    m = ChatMessage(conversation_id=conversation.id, created_utc=now, role=role, content=content, meta=meta)
    session.add(m)
    conversation.updated_utc = now
    session.flush()
    return m


def chat_history(session: Session, conversation_id: int) -> list[tuple[str, str]]:
    rows = session.execute(select(ChatMessage.role, ChatMessage.content)
                           .where(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.id)).all()
    return [(r, c) for r, c in rows]


def list_conversations(session: Session, settings: Settings, limit: int = 30) -> list[dict]:
    q = select(Conversation).order_by(Conversation.updated_utc.desc()).limit(limit)
    return [{"id": c.id, "titulo": c.title, "provedor": c.provider, "atualizada": _local(c.updated_utc, settings)}
            for c in session.scalars(q)]


def conversation_detail(session: Session, settings: Settings, conversation_id: int) -> dict | None:
    c = session.get(Conversation, conversation_id)
    if c is None:
        return None
    return {"id": c.id, "titulo": c.title, "provedor": c.provider, "criada": _local(c.created_utc, settings),
            "mensagens": [{"papel": m.role, "texto": m.content, "quando": _local(m.created_utc, settings),
                           "ferramentas": (m.meta or {}).get("ferramentas")} for m in c.messages]}
