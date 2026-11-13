"""Aderência ao plano: casa sessões planejadas com treinos feitos e compara com as metas (ADR 0010).

Cálculo puro: recebe listas de dataclasses e devolve dicts. Nada é gravado; o casamento é refeito a cada consulta.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from .formato import pace_str

SEM_TREINO = ("rest",)          # esporte de sessão de descanso
TOLERANCIA_PCT = 10             # distância/duração dentro de +-10% do alvo conta como "no alvo"
ZONAS = ("z1", "z2", "z3", "z4", "z5")


@dataclass
class Sessao:
    id: int
    day: date
    sport: str
    kind: str
    status: str = "planejada"                 # planejada, cancelada
    description: str | None = None
    target_distance_km: float | None = None
    target_duration_min: float | None = None
    target_pace_min_s_km: float | None = None  # mais rápido aceito
    target_pace_max_s_km: float | None = None  # mais lento aceito
    target_hr_zone: str | None = None
    target_rpe: float | None = None


@dataclass
class Treino:
    id: int
    day: date                                  # dia no fuso local
    sport: str
    name: str | None = None
    distance_km: float | None = None
    duration_min: float | None = None
    pace_s_km: float | None = None
    zones_s: dict = field(default_factory=dict)
    rpe: float | None = None


def _casar(sessoes: list[Sessao], treinos: list[Treino]) -> dict[int, tuple[Treino, bool]]:
    """sessão.id -> (treino, mesmo_dia). Primeiro o mesmo dia; depois dia anterior e seguinte."""
    livres = sorted(treinos, key=lambda t: (t.day, t.id))
    usados: set[int] = set()
    casados: dict[int, tuple[Treino, bool]] = {}
    alvos = [s for s in sorted(sessoes, key=lambda s: (s.day, s.id))
             if s.status != "cancelada" and s.sport not in SEM_TREINO]
    for deslocamentos, mesmo_dia in (((0,), True), ((-1, 1), False)):
        for s in alvos:
            if s.id in casados:
                continue
            for d in deslocamentos:
                dia = s.day + timedelta(days=d)
                t = next((t for t in livres if t.id not in usados and t.sport == s.sport and t.day == dia), None)
                if t:
                    casados[s.id] = (t, mesmo_dia)
                    usados.add(t.id)
                    break
    return casados


def _pct(feito: float | None, alvo: float | None) -> int | None:
    return round(100 * feito / alvo) if feito is not None and alvo else None


def _comparar(s: Sessao, t: Treino) -> dict:
    out: dict = {}
    if s.target_distance_km:
        out["distancia"] = {"alvo_km": s.target_distance_km, "feito_km": round(t.distance_km or 0, 2),
                            "pct": _pct(t.distance_km, s.target_distance_km)}
    if s.target_duration_min:
        out["duracao"] = {"alvo_min": s.target_duration_min, "feito_min": round(t.duration_min or 0, 1),
                          "pct": _pct(t.duration_min, s.target_duration_min)}
    if (s.target_pace_min_s_km or s.target_pace_max_s_km) and t.pace_s_km:
        lo, hi = s.target_pace_min_s_km, s.target_pace_max_s_km
        if lo and t.pace_s_km < lo:
            situacao = "mais_rapido"
        elif hi and t.pace_s_km > hi:
            situacao = "mais_lento"
        else:
            situacao = "dentro"
        out["ritmo"] = {"alvo": f"{pace_str(lo) or '-'} a {pace_str(hi) or '-'}", "feito": pace_str(t.pace_s_km),
                        "situacao": situacao}
    if s.target_hr_zone and t.zones_s:
        total = sum(v for k, v in t.zones_s.items() if k in ZONAS)
        if total:
            i = ZONAS.index(s.target_hr_zone)
            na = t.zones_s.get(s.target_hr_zone, 0)
            acima = sum(t.zones_s.get(z, 0) for z in ZONAS[i + 1:])
            out["zona_fc"] = {"alvo": s.target_hr_zone, "pct_na_zona": round(100 * na / total),
                              "pct_acima": round(100 * acima / total),
                              "pct_abaixo": round(100 * (total - na - acima) / total)}
    if s.target_rpe and t.rpe:
        out["esforco"] = {"alvo": s.target_rpe, "feito": t.rpe}
    return out


def _no_alvo(comp: dict) -> bool | None:
    """True se tudo que tem meta ficou no alvo; None se a sessão não tinha metas comparáveis."""
    checks = []
    for k in ("distancia", "duracao"):
        if k in comp and comp[k]["pct"] is not None:
            checks.append(abs(comp[k]["pct"] - 100) <= TOLERANCIA_PCT or comp[k]["pct"] > 100)
    if "ritmo" in comp:
        checks.append(comp["ritmo"]["situacao"] == "dentro")
    if "zona_fc" in comp:
        checks.append(comp["zona_fc"]["pct_acima"] <= 20)
    return all(checks) if checks else None


def aderencia(sessoes: list[Sessao], treinos: list[Treino], inicio: date, fim: date, hoje: date) -> dict:
    """`treinos` deve vir sem duplicatas e cobrir de inicio-1 a fim+1 (para o casamento em dia vizinho)."""
    casados = _casar(sessoes, treinos)
    usados = {t.id for t, _ in casados.values()}
    linhas = []
    for s in sorted(sessoes, key=lambda s: (s.day, s.id)):
        linha = {"sessao_id": s.id, "dia": s.day.isoformat(), "esporte": s.sport, "tipo": s.kind,
                 "descricao": s.description}
        if s.status == "cancelada":
            linha["status"] = "cancelada"
        elif s.sport in SEM_TREINO:
            linha["status"] = "descanso"
        elif s.id in casados:
            t, mesmo_dia = casados[s.id]
            comp = _comparar(s, t)
            linha.update(status="feita" if mesmo_dia else "feita_outro_dia", treino_id=t.id,
                         treino_dia=t.day.isoformat(), comparacao=comp or None, no_alvo=_no_alvo(comp))
        else:
            linha["status"] = "futura" if s.day > hoje else ("pendente_hoje" if s.day == hoje else "perdida")
        linhas.append({k: v for k, v in linha.items() if v is not None})

    extras = [{"treino_id": t.id, "dia": t.day.isoformat(), "esporte": t.sport, "nome": t.name,
               "distancia_km": round(t.distance_km, 2) if t.distance_km else None}
              for t in sorted(treinos, key=lambda t: (t.day, t.id))
              if t.id not in usados and inicio <= t.day <= fim]

    semanas: dict[date, dict] = {}
    seg0 = inicio - timedelta(days=inicio.weekday())
    d = seg0
    while d <= fim:
        semanas[d] = {"semana": d.isoformat(), "planejadas": 0, "feitas": 0, "perdidas": 0, "no_alvo": 0,
                      "km_planejados": 0.0, "km_feitos": 0.0}
        d += timedelta(weeks=1)
    for s, linha in zip(sorted(sessoes, key=lambda s: (s.day, s.id)), linhas):
        w = semanas[s.day - timedelta(days=s.day.weekday())]
        if linha["status"] in ("cancelada", "descanso"):
            continue
        w["planejadas"] += 1
        w["km_planejados"] += s.target_distance_km or 0
        if linha["status"].startswith("feita"):
            w["feitas"] += 1
            w["no_alvo"] += bool(linha.get("no_alvo"))
        elif linha["status"] == "perdida":
            w["perdidas"] += 1
    for t in treinos:
        if inicio <= t.day <= fim and t.distance_km:
            semanas[t.day - timedelta(days=t.day.weekday())]["km_feitos"] += t.distance_km
    for w in semanas.values():
        w["km_planejados"], w["km_feitos"] = round(w["km_planejados"], 1), round(w["km_feitos"], 1)

    vencidas = [l for l in linhas if l["status"] in ("feita", "feita_outro_dia", "perdida")]
    feitas = [l for l in vencidas if l["status"] != "perdida"]
    return {
        "resumo": {"sessoes_vencidas": len(vencidas), "feitas": len(feitas),
                   "perdidas": len(vencidas) - len(feitas),
                   "pct_feitas": round(100 * len(feitas) / len(vencidas)) if vencidas else None,
                   "feitas_no_alvo": sum(1 for l in feitas if l.get("no_alvo")),
                   "futuras": sum(1 for l in linhas if l["status"] in ("futura", "pendente_hoje")),
                   "extras": len(extras)},
        "semanas": list(semanas.values()),
        "sessoes": linhas,
        "extras": extras,
    }
