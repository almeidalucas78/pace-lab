"""Regras de negócio e consultas. CLI, API, agendador, MCP e chat chamam só daqui."""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session, selectinload

from .config import Settings
from .core.formato import pace_str
from .core.load import (ENDURANCE_SPORTS, ZONES, daily_series, estimate_fc_max, trimp_from_average,
                        trimp_from_zones, zones_from_samples)
from .core.aderencia import Sessao, Treino, aderencia
from .db.models import (Activity, ChatMessage, Conversation, DailyLoad, PlannedSession, Sample, Sensation, Split,
                        SyncState, TrainingPlan)
from .ingest.treinos_app import converter as converter_treino_app, gravar as gravar_treinos_app

DUPLICATE_WINDOW = timedelta(minutes=10)
# menor vence quando o mesmo treino vem de mais de uma fonte (ADR 0003): o Strava continua prevalecendo
SOURCE_PRIORITY = {"strava": 0, "samsung_health": 1, "health_connect": 2}


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


# ---------- situação da sincronização do app ----------

def sync_status(session: Session, settings: Settings) -> dict:
    """Última sincronização de cada fonte do app Android (o celular envia; o PC só registra)."""
    fontes = []
    for fonte in ("samsung_health", "health_connect"):
        st = session.get(SyncState, fonte)
        if st is None:
            continue
        fontes.append({
            "fonte": fonte,
            "ultimo_sucesso": _local(st.last_success_utc, settings) if st.last_success_utc else None,
            "ultima_tentativa": _local(st.last_attempt_utc, settings) if st.last_attempt_utc else None,
            "ultimo_erro": st.last_error,
            "ultimo_resultado": st.last_result,
        })
    return {"fontes": fontes, "aviso": None if fontes else "o app ainda não enviou treinos"}


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


# ---------- planos de treino e aderência (ADR 0010) ----------

PLAN_SPORTS = {"run", "walk", "ride", "strength", "workout", "rest"}
PLAN_KINDS = {"rodagem", "longao", "intervalado", "ritmo", "regenerativo", "descanso", "musculacao", "outro"}
HR_ZONES = {"z1", "z2", "z3", "z4", "z5"}
SESSION_FIELDS = ("day", "sport", "kind", "description", "target_distance_km", "target_duration_min",
                  "target_pace_min_s_km", "target_pace_max_s_km", "target_hr_zone", "target_rpe", "notes")
WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def parse_pace(value: str | float | None) -> float | None:
    """'5:30' ou '5:30/km' viram 330 s/km. Número já em s/km passa direto."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    txt = str(value).strip().removesuffix("/km").strip()
    try:
        m, s = txt.split(":")
        secs = int(m) * 60 + int(s)
    except ValueError:
        raise ValueError(f"ritmo inválido: {value!r} (use m:ss, ex.: 5:30)")
    if not 120 <= secs <= 1200:
        raise ValueError(f"ritmo fora do razoável: {value!r}")
    return float(secs)


def _check_session(s: PlannedSession, plan: TrainingPlan) -> None:
    if not plan.start_date <= s.day <= plan.end_date:
        raise ValueError(f"sessão em {s.day} fora do plano ({plan.start_date} a {plan.end_date})")
    if s.sport not in PLAN_SPORTS:
        raise ValueError(f"esporte inválido: {s.sport} (use {', '.join(sorted(PLAN_SPORTS))})")
    if s.sport == "rest":
        s.kind = "descanso"
    if s.kind not in PLAN_KINDS:
        raise ValueError(f"tipo inválido: {s.kind} (use {', '.join(sorted(PLAN_KINDS))})")
    if s.target_hr_zone and s.target_hr_zone not in HR_ZONES:
        raise ValueError(f"zona inválida: {s.target_hr_zone} (use z1 a z5)")
    if s.target_rpe is not None and not 1 <= s.target_rpe <= 10:
        raise ValueError("esforço alvo vai de 1 a 10")
    lo, hi = s.target_pace_min_s_km, s.target_pace_max_s_km
    if lo and hi and lo > hi:
        raise ValueError("faixa de ritmo invertida: o mínimo (mais rápido) deve ser menor que o máximo")


def _session_dict(s: PlannedSession) -> dict:
    d = {"id": s.id, "dia": s.day.isoformat(), "dia_semana": WEEKDAYS[s.day.weekday()], "esporte": s.sport,
         "tipo": s.kind, "descricao": s.description, "distancia_km": s.target_distance_km,
         "duracao_min": s.target_duration_min,
         "ritmo": (f"{pace_str(s.target_pace_min_s_km) or '-'} a {pace_str(s.target_pace_max_s_km) or '-'}"
                   if s.target_pace_min_s_km or s.target_pace_max_s_km else None),
         "zona_fc": s.target_hr_zone, "esforco": s.target_rpe, "notas": s.notes,
         "status": s.status if s.status != "planejada" else None}
    return {k: v for k, v in d.items() if v is not None}


def plan_dict(plan: TrainingPlan, settings: Settings, with_sessions: bool = True) -> dict:
    d = {"id": plan.id, "titulo": plan.title, "objetivo": plan.goal, "inicio": plan.start_date.isoformat(),
         "fim": plan.end_date.isoformat(), "status": plan.status, "substituido_por": plan.replaced_by,
         "conversa_id": plan.conversation_id, "notas": plan.notes, "criado": _local(plan.created_utc, settings)}
    d = {k: v for k, v in d.items() if v is not None}
    if with_sessions:
        d["sessoes"] = [_session_dict(s) for s in plan.sessions]
    return d


def create_plan(session: Session, settings: Settings, title: str, start: date, end: date, sessions: list[dict],
                goal: str | None = None, notes: str | None = None, conversation_id: int | None = None) -> dict:
    """Cria o plano e o torna o ativo; o ativo anterior fica "substituido" apontando para este."""
    if end < start:
        raise ValueError("o fim do plano é antes do início")
    if (end - start).days > 366:
        raise ValueError("plano com mais de um ano; divida em blocos")
    if not sessions:
        raise ValueError("plano sem sessões")
    now = datetime.now(timezone.utc)
    plan = TrainingPlan(created_utc=now, updated_utc=now, title=title.strip()[:200], goal=goal, start_date=start,
                        end_date=end, status="ativo", notes=notes, conversation_id=conversation_id)
    for raw in sessions:
        s = PlannedSession(status="planejada", **{k: raw.get(k) for k in SESSION_FIELDS})
        _check_session(s, plan)
        plan.sessions.append(s)
    previous = session.scalars(select(TrainingPlan).where(TrainingPlan.status == "ativo")).all()
    session.add(plan)
    session.flush()
    for p in previous:
        p.status, p.replaced_by, p.updated_utc = "substituido", plan.id, now
    session.flush()
    return plan_dict(plan, settings)


def active_plan(session: Session) -> TrainingPlan | None:
    return session.scalar(select(TrainingPlan).where(TrainingPlan.status == "ativo")
                          .order_by(TrainingPlan.id.desc()).limit(1))


def get_plan(session: Session, plan_id: int | None) -> TrainingPlan:
    """Plano pelo id, ou o ativo quando plan_id é None."""
    plan = active_plan(session) if plan_id is None else session.get(TrainingPlan, plan_id)
    if plan is None:
        raise ValueError("nenhum plano ativo" if plan_id is None else f"plano {plan_id} não existe")
    return plan


def list_plans(session: Session, settings: Settings, limit: int = 20) -> list[dict]:
    q = select(TrainingPlan).order_by(TrainingPlan.id.desc()).limit(limit)
    return [plan_dict(p, settings, with_sessions=False) for p in session.scalars(q)]


def add_session(session: Session, settings: Settings, plan_id: int | None, data: dict) -> dict:
    plan = get_plan(session, plan_id)
    s = PlannedSession(status="planejada", **{k: data.get(k) for k in SESSION_FIELDS})
    _check_session(s, plan)
    plan.sessions.append(s)
    plan.updated_utc = datetime.now(timezone.utc)
    session.flush()
    return _session_dict(s)


def update_session(session: Session, settings: Settings, session_id: int, changes: dict,
                   cancel: bool = False, reactivate: bool = False) -> dict:
    """Ajuste pontual: muda só os campos presentes em `changes` (valor None limpa a meta)."""
    s = session.get(PlannedSession, session_id)
    if s is None:
        raise ValueError(f"sessão {session_id} não existe")
    for k, v in changes.items():
        if k not in SESSION_FIELDS:
            raise ValueError(f"campo desconhecido: {k}")
        setattr(s, k, v)
    if cancel:
        s.status = "cancelada"
    elif reactivate:
        s.status = "planejada"
    _check_session(s, s.plan)
    s.plan.updated_utc = datetime.now(timezone.utc)
    session.flush()
    return _session_dict(s)


def archive_plan(session: Session, settings: Settings, plan_id: int | None) -> dict:
    """Encerra o plano sem apagar (fica no histórico). Sem plano ativo até salvar outro."""
    plan = get_plan(session, plan_id)
    plan.status, plan.updated_utc = "arquivado", datetime.now(timezone.utc)
    session.flush()
    return plan_dict(plan, settings, with_sessions=False)


def link_plans_to_conversation(session: Session, conversation_id: int, since: datetime) -> None:
    """Planos criados durante uma resposta do chat ficam ligados à conversa em que nasceram."""
    for p in session.scalars(select(TrainingPlan).where(TrainingPlan.conversation_id.is_(None),
                                                        TrainingPlan.created_utc >= since)):
        p.conversation_id = conversation_id


def plan_adherence(session: Session, settings: Settings, plan_id: int | None = None,
                   today: date | None = None) -> dict:
    plan = get_plan(session, plan_id)
    tz = settings.tz
    lo = datetime.combine(plan.start_date - timedelta(days=1), datetime.min.time(), tzinfo=tz)
    hi = datetime.combine(plan.end_date + timedelta(days=2), datetime.min.time(), tzinfo=tz)
    acts = session.scalars(select(Activity).where(Activity.start_utc >= lo, Activity.start_utc < hi,
                                                  Activity.possible_duplicate_of.is_(None))).all()
    treinos = []
    for a in acts:
        km = a.distance_m / 1000 if a.distance_m else None
        treinos.append(Treino(
            id=a.id, day=a.start_utc.astimezone(tz).date(), sport=a.sport, name=a.name, distance_km=km,
            duration_min=a.moving_s / 60 if a.moving_s else None,
            pace_s_km=a.moving_s / km if km and a.moving_s and a.sport in ("run", "walk") else None,
            zones_s=a.hr_zones_s or {}, rpe=a.rpe))
    sessoes = [Sessao(id=s.id, day=s.day, sport=s.sport, kind=s.kind, status=s.status, description=s.description,
                      target_distance_km=s.target_distance_km, target_duration_min=s.target_duration_min,
                      target_pace_min_s_km=s.target_pace_min_s_km, target_pace_max_s_km=s.target_pace_max_s_km,
                      target_hr_zone=s.target_hr_zone, target_rpe=s.target_rpe) for s in plan.sessions]
    rep = aderencia(sessoes, treinos, plan.start_date, plan.end_date, today or datetime.now(tz).date())
    _, origem = resolve_fc_max(session, settings)
    out = {"plano": plan_dict(plan, settings, with_sessions=False), **rep}
    if origem == "estimada":
        out["observacao"] = "zonas de FC calculadas com FC máxima ESTIMADA"
    return out


# ---------- treinos enviados pelo app Android (ADR 0013) ----------

def receive_app_workouts(session: Session, settings: Settings, fonte: str, treinos: list[dict],
                         apagados: list[str] | None = None, now: datetime | None = None) -> dict:
    """Grava os treinos lidos no celular, recalcula a carga e registra a sincronização da fonte.
    Devolve os treinos novos que não são duplicata (para a notificação)."""
    now = now or datetime.now(timezone.utc)
    recebidos = [converter_treino_app(fonte, t) for t in treinos]
    rep = gravar_treinos_app(session, recebidos, [(fonte, i) for i in apagados or []])
    rc = recompute(session, settings)
    novos = [activity_summary(a, settings) for a in
             session.scalars(select(Activity).where(Activity.id.in_(rep["novos_ids"]),
                                                    Activity.possible_duplicate_of.is_(None))
                             .order_by(Activity.start_utc))]
    result = {"status": "ok", "fonte": fonte, "recebidos": len(recebidos), "novos": len(rep["novos_ids"]),
              "novos_duplicados": len(rep["novos_ids"]) - len(novos), "atualizados": rep["atualizados"],
              "apagados": rep["apagados"], "fc_max": rc["fc_max"], "fc_max_origem": rc["fc_max_origem"]}
    st = session.get(SyncState, fonte) or SyncState(source=fonte)
    session.add(st)
    st.last_attempt_utc = st.last_success_utc = now
    st.last_error, st.last_result = None, result
    return {**result, "treinos_novos": novos}


def reprocess_app_workouts(session: Session, settings: Settings) -> dict:
    """Refaz amostras, parciais e qualidade dos treinos vindos do app a partir das leituras guardadas
    (ex.: depois de corrigir o conversor). Não precisa reenviar nada do celular."""
    from .ingest.files import Point
    from .ingest.streams_store import save_streams
    from .ingest.treinos_app import FONTES, gps_valido, mesclar_proximos

    feitos = 0
    for a in session.scalars(select(Activity).where(Activity.source.in_(FONTES))).all():
        amostras = session.scalars(select(Sample).where(Sample.activity_id == a.id).order_by(Sample.t_s)).all()
        if not amostras:
            continue
        pontos = [Point(time=a.start_utc + timedelta(seconds=s.t_s),
                        lat=s.lat if gps_valido(s.lat, s.lon) else None,
                        lon=s.lon if gps_valido(s.lat, s.lon) else None,
                        ele=s.ele_m if gps_valido(s.lat, s.lon) else None,
                        hr=s.hr_raw, cadence=s.cadence_spm, speed=s.speed_ms) for s in amostras]
        pontos = mesclar_proximos(pontos)
        save_streams(session, a, pontos, a.source)
        extra = dict(a.extra or {})
        extra["pontos_gps"] = sum(1 for p in pontos if p.lat is not None)
        a.extra = extra
        feitos += 1
    rc = recompute(session, settings)
    return {"reprocessados": feitos, "fc_max": rc["fc_max"]}


# --- App Android: atualização pelo próprio app (fase 7, etapa 4b) ---

APK_NOME = "pace-lab.apk"


def publish_app(settings: Settings, pasta_build: Path, now: datetime | None = None) -> dict:
    """Copia o APK do build do Gradle para a pasta do app e grava a versão (lida do `output-metadata.json`,
    que o Android Gradle Plugin escreve ao lado do APK). Não aceita versão menor que a já publicada."""
    meta_path = Path(pasta_build) / "output-metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"{meta_path} não existe; compile o app antes (gradlew assembleDebug)")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("applicationId") != "app.pacelab" or not meta.get("elements"):
        raise ValueError("o build não é do app Pace Lab")
    el = meta["elements"][0]
    apk = Path(pasta_build) / el["outputFile"]
    codigo = int(el["versionCode"])
    atual = app_version(settings)
    if atual and codigo < atual["codigo"]:
        raise ValueError(f"versão {codigo} é menor que a publicada ({atual['codigo']})")
    pasta = settings.app_dir
    pasta.mkdir(parents=True, exist_ok=True)
    dados = apk.read_bytes()
    (pasta / APK_NOME).write_bytes(dados)
    info = {"codigo": codigo, "nome": el.get("versionName"), "tamanho": len(dados),
            "sha256": hashlib.sha256(dados).hexdigest(),
            "publicado_em": (now or datetime.now(timezone.utc)).astimezone(settings.tz).isoformat(timespec="minutes")}
    (pasta / "versao.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return info


def app_version(settings: Settings) -> dict | None:
    p = settings.app_dir / "versao.json"
    if not p.exists() or not (settings.app_dir / APK_NOME).exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def app_apk_path(settings: Settings) -> Path | None:
    p = settings.app_dir / APK_NOME
    return p if p.exists() else None
