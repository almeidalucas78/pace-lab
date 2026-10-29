"""Ferramentas da IA: as mesmas no servidor MCP e no chat do painel (Claude e Gemini).

Cada ferramenta chama só `services` e devolve uma ficha resumida (nunca amostras brutas), para gastar pouco token.
O esquema JSON de cada uma sai das anotações de tipo, então existe um único lugar para mudar.
"""
from __future__ import annotations

import inspect
import typing
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any, Callable, Literal

from pydantic import BaseModel, Field, ValidationError, create_model

from .. import services
from ..config import get_settings
from ..db import session_scope

Esporte = Annotated[str, Field(description="run (corrida), walk (caminhada), ride (pedalada), strength (musculação), "
                                           "workout (treino genérico) ou todos")]
Data = Annotated[str | None, Field(description="data no formato AAAA-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$")]


@dataclass
class Ferramenta:
    nome: str
    descricao: str
    funcao: Callable[..., Any]
    somente_leitura: bool

    @property
    def modelo(self):
        hints = typing.get_type_hints(self.funcao, include_extras=True)
        campos = {}
        for p in inspect.signature(self.funcao).parameters.values():
            padrao = ... if p.default is inspect.Parameter.empty else p.default
            campos[p.name] = (hints[p.name], padrao)
        return create_model(self.nome, **campos)

    @property
    def schema(self) -> dict:
        schema = self.modelo.model_json_schema()
        defs = schema.pop("$defs", {})
        return _sem_titulos(_expandir_refs(schema, defs))


REGISTRO: list[Ferramenta] = []


def ferramenta(descricao: str, somente_leitura: bool = True):
    def registrar(fn):
        REGISTRO.append(Ferramenta(fn.__name__, descricao, fn, somente_leitura))
        return fn
    return registrar


def _sem_titulos(schema: Any) -> Any:
    if isinstance(schema, dict):
        return {k: _sem_titulos(v) for k, v in schema.items() if k != "title"}
    if isinstance(schema, list):
        return [_sem_titulos(v) for v in schema]
    return schema


def _expandir_refs(schema: Any, defs: dict) -> Any:
    """Troca {"$ref": "#/$defs/X"} pela definição (nem todo provedor aceita $ref)."""
    if isinstance(schema, dict):
        if "$ref" in schema:
            return _expandir_refs(defs[schema["$ref"].rsplit("/", 1)[-1]], defs)
        return {k: _expandir_refs(v, defs) for k, v in schema.items()}
    if isinstance(schema, list):
        return [_expandir_refs(v, defs) for v in schema]
    return schema


def _esporte(esporte: str) -> str | None:
    return None if esporte == "todos" else esporte


def executar(nome: str, args: dict | None) -> Any:
    """Valida os argumentos e roda a ferramenta. Erro vira {"erro": ...} para a IA poder reagir."""
    f = next((f for f in REGISTRO if f.nome == nome), None)
    if f is None:
        return {"erro": f"ferramenta desconhecida: {nome}"}
    try:
        validados = f.modelo.model_validate(args or {})
        return f.funcao(**validados.model_dump())
    except ValidationError as e:
        return {"erro": "argumentos inválidos: " + "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())}
    except ValueError as e:
        return {"erro": str(e)}


# ---------- ferramentas ----------

@ferramenta("Ficha do treino mais recente (ignora duplicatas): totais, ritmo, FC, zonas, carga, parciais por km "
            "e sensações registradas.")
def ultimo_treino(esporte: Esporte = "run") -> dict:
    with session_scope() as s:
        aid = services.last_activity_id(s, _esporte(esporte))
        if aid is None:
            return {"aviso": "nenhum treino encontrado"}
        return services.activity_card(s, get_settings(), aid)


@ferramenta("Ficha completa de um treino pelo id: totais, ritmo, FC, zonas, carga, parciais por km, qualidade da FC "
            "e sensações registradas.")
def detalhe_treino(treino_id: Annotated[int, Field(description="id do treino")]) -> dict:
    with session_scope() as s:
        card = services.activity_card(s, get_settings(), treino_id)
    return card or {"erro": f"treino {treino_id} não encontrado"}


@ferramenta("Lista resumida de treinos, do mais recente para o mais antigo (sem duplicatas).")
def listar_treinos(esporte: Esporte = "run",
                   limite: Annotated[int, Field(ge=1, le=50, description="quantos treinos")] = 10,
                   desde: Data = None) -> list[dict]:
    with session_scope() as s:
        rows = services.list_activities(s, get_settings(), _esporte(esporte), limite,
                                        since=date.fromisoformat(desde) if desde else None,
                                        include_duplicates=False)
    keys = ("id", "data", "esporte", "nome", "distancia_km", "tempo_movimento_min", "ritmo", "fc_media", "carga",
            "qualidade_fc")
    return [{k: r[k] for k in keys if r[k] is not None} for r in rows]


@ferramenta("Volume por semana (segunda a domingo): treinos, km, tempo, ritmo médio, maior treino e carga.")
def resumo_semanas(semanas: Annotated[int, Field(ge=1, le=52, description="quantas semanas, contando a atual")] = 8,
                   esporte: Esporte = "run") -> list[dict]:
    with session_scope() as s:
        return services.weekly_summary(s, get_settings(), semanas, esporte if esporte != "todos" else "run")


@ferramenta("Carga de treino atual: fitness, fadiga e forma de hoje, comparação com 7 e 28 dias atrás e carga "
            "diária das últimas duas semanas.")
def carga_atual() -> dict:
    with session_scope() as s:
        return services.current_load(s, get_settings())


@ferramenta("Perfil do atleta: FC máxima usada nos cálculos (e se é medida ou estimada), zonas de FC em bpm e "
            "visão geral do histórico.")
def perfil_atleta() -> dict:
    with session_scope() as s:
        return services.athlete_profile(s, get_settings())


@ferramenta("Registra como o usuário se sentiu: cansaço, dor, sono, disposição, percepção de esforço. Use quando ele "
            "contar algo assim. Sem treino_id e sem data, vale para hoje.", somente_leitura=False)
def registrar_sensacao(texto: Annotated[str, Field(min_length=1, description="o relato, nas palavras do usuário")],
                       rpe: Annotated[float | None, Field(ge=1, le=10, description="percepção de esforço de 1 a 10")] = None,
                       treino_id: Annotated[int | None, Field(description="treino a que se refere, se houver")] = None,
                       data: Data = None,
                       tags: Annotated[list[str] | None, Field(description="marcadores curtos, ex.: dor_joelho, sono_ruim")] = None,
                       ) -> dict:
    with session_scope() as s:
        return services.add_sensation(s, get_settings(), texto, rpe, treino_id,
                                      date.fromisoformat(data) if data else None, tags)


@ferramenta("Sensações registradas nos últimos dias (cansaço, dores, percepção de esforço).")
def ver_sensacoes(dias: Annotated[int, Field(ge=1, le=365, description="quantos dias para trás")] = 30) -> list[dict]:
    with session_scope() as s:
        return services.list_sensations(s, get_settings(), days=dias)


@ferramenta("Quando foi a última sincronização com o celular (Health Connect) e se deu erro. Use se o usuário "
            "disser que um treino recente não aparece.")
def status_sincronizacao() -> dict:
    with session_scope() as s:
        return services.sync_status(s, get_settings())


# ---------- planos de treino (ADR 0010) ----------

DataObrig = Annotated[str, Field(description="data no formato AAAA-MM-DD", pattern=r"^\d{4}-\d{2}-\d{2}$")]
Ritmo = Annotated[str | None, Field(description="ritmo em min:seg por km, ex.: 5:30", pattern=r"^\d{1,2}:\d{2}$")]
EsportePlano = Literal["run", "walk", "ride", "strength", "workout", "rest"]
TipoSessao = Literal["rodagem", "longao", "intervalado", "ritmo", "regenerativo", "descanso", "musculacao", "outro"]
Zona = Literal["z1", "z2", "z3", "z4", "z5"]
PlanoId = Annotated[int | None, Field(description="id do plano; vazio = plano ativo")]


class SessaoIn(BaseModel):
    """Uma sessão do plano. Todas as metas são opcionais: use só as que fazem sentido."""
    dia: DataObrig
    esporte: Annotated[EsportePlano, Field(description="rest = descanso")]
    tipo: TipoSessao
    descricao: Annotated[str | None, Field(description="o que fazer, ex.: 6x800 m com 2 min de trote")] = None
    distancia_km: Annotated[float | None, Field(gt=0, le=100)] = None
    duracao_min: Annotated[float | None, Field(gt=0, le=600)] = None
    ritmo_min: Annotated[Ritmo, Field(description="ritmo mais rápido aceito, ex.: 5:30")] = None
    ritmo_max: Annotated[Ritmo, Field(description="ritmo mais lento aceito, ex.: 5:50")] = None
    zona_fc: Annotated[Zona | None, Field(description="zona de FC alvo")] = None
    esforco: Annotated[float | None, Field(ge=1, le=10, description="percepção de esforço alvo, 1 a 10")] = None
    notas: str | None = None


def _sessao_para_servico(x: SessaoIn | dict) -> dict:
    x = x.model_dump() if isinstance(x, BaseModel) else x
    return {"day": date.fromisoformat(x["dia"]), "sport": x["esporte"], "kind": x["tipo"],
            "description": x.get("descricao"), "target_distance_km": x.get("distancia_km"),
            "target_duration_min": x.get("duracao_min"),
            "target_pace_min_s_km": services.parse_pace(x.get("ritmo_min")),
            "target_pace_max_s_km": services.parse_pace(x.get("ritmo_max")),
            "target_hr_zone": x.get("zona_fc"), "target_rpe": x.get("esforco"), "notes": x.get("notas")}


@ferramenta("Salva um plano de treino NOVO e o torna o plano ativo (o ativo anterior fica como substituído, no "
            "histórico). Só chame depois de mostrar o plano ao usuário e ele confirmar. Inclua todas as sessões, "
            "inclusive descansos. Para ajustes pequenos num plano existente, use alterar_sessao ou adicionar_sessao.",
            somente_leitura=False)
def salvar_plano(titulo: Annotated[str, Field(min_length=1, max_length=200)],
                 inicio: DataObrig, fim: DataObrig,
                 sessoes: Annotated[list[SessaoIn], Field(min_length=1, max_length=400)],
                 objetivo: Annotated[str | None, Field(description="objetivo do plano, ex.: 10 km em 50 min")] = None,
                 notas: str | None = None) -> dict:
    with session_scope() as s:
        return services.create_plan(s, get_settings(), titulo, date.fromisoformat(inicio), date.fromisoformat(fim),
                                    [_sessao_para_servico(x) for x in sessoes], objetivo, notas)


@ferramenta("Plano de treino ativo (ou outro, pelo id) com todas as sessões e metas.")
def plano_atual(plano_id: PlanoId = None) -> dict:
    with session_scope() as s:
        return services.plan_dict(services.get_plan(s, plano_id), get_settings())


@ferramenta("Aderência ao plano: para cada sessão, se foi feita (no dia ou em dia vizinho), perdida, futura ou "
            "cancelada, comparando distância, duração, ritmo e zona de FC com as metas; treinos extras; resumo "
            "por semana.")
def aderencia_plano(plano_id: PlanoId = None) -> dict:
    with session_scope() as s:
        return services.plan_adherence(s, get_settings(), plano_id)


@ferramenta("Ajuste pontual numa sessão existente: mover de dia, mudar metas, cancelar ou reativar. Só os campos "
            "informados mudam; para apagar uma meta, ponha o nome do campo em 'limpar'.", somente_leitura=False)
def alterar_sessao(sessao_id: Annotated[int, Field(description="id da sessão (veja plano_atual)")],
                   dia: Data = None, tipo: TipoSessao | None = None, descricao: str | None = None,
                   distancia_km: Annotated[float | None, Field(gt=0, le=100)] = None,
                   duracao_min: Annotated[float | None, Field(gt=0, le=600)] = None,
                   ritmo_min: Ritmo = None, ritmo_max: Ritmo = None, zona_fc: Zona | None = None,
                   esforco: Annotated[float | None, Field(ge=1, le=10)] = None, notas: str | None = None,
                   limpar: Annotated[list[Literal["distancia_km", "duracao_min", "ritmo_min", "ritmo_max", "zona_fc",
                                                  "esforco", "descricao", "notas"]] | None,
                                     Field(description="metas a apagar")] = None,
                   cancelar: bool = False, reativar: bool = False) -> dict:
    campos = {"day": date.fromisoformat(dia) if dia else None, "kind": tipo, "description": descricao,
              "target_distance_km": distancia_km, "target_duration_min": duracao_min,
              "target_pace_min_s_km": services.parse_pace(ritmo_min),
              "target_pace_max_s_km": services.parse_pace(ritmo_max),
              "target_hr_zone": zona_fc, "target_rpe": esforco, "notes": notas}
    mudancas = {k: v for k, v in campos.items() if v is not None}
    nomes = {"distancia_km": "target_distance_km", "duracao_min": "target_duration_min",
             "ritmo_min": "target_pace_min_s_km", "ritmo_max": "target_pace_max_s_km", "zona_fc": "target_hr_zone",
             "esforco": "target_rpe", "descricao": "description", "notas": "notes"}
    mudancas.update({nomes[c]: None for c in limpar or []})
    with session_scope() as s:
        return services.update_session(s, get_settings(), sessao_id, mudancas, cancel=cancelar, reactivate=reativar)


@ferramenta("Acrescenta uma sessão a um plano existente (por padrão, o ativo).", somente_leitura=False)
def adicionar_sessao(sessao: SessaoIn, plano_id: PlanoId = None) -> dict:
    with session_scope() as s:
        return services.add_session(s, get_settings(), plano_id, _sessao_para_servico(sessao))


@ferramenta("Encerra um plano sem apagar (fica no histórico como arquivado); depois não há plano ativo até salvar "
            "outro. Só chame se o usuário pedir para encerrar ou descartar o plano.", somente_leitura=False)
def arquivar_plano(plano_id: PlanoId = None) -> dict:
    with session_scope() as s:
        return services.archive_plan(s, get_settings(), plano_id)


@ferramenta("Histórico de planos (ativo, substituídos e arquivados), sem as sessões.")
def listar_planos(limite: Annotated[int, Field(ge=1, le=50)] = 10) -> list[dict]:
    with session_scope() as s:
        return services.list_plans(s, get_settings(), limite)
