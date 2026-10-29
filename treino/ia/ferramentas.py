"""Ferramentas da IA: as mesmas no servidor MCP e no chat do painel (Claude e Gemini).

Cada ferramenta chama só `services` e devolve uma ficha resumida (nunca amostras brutas), para gastar pouco token.
O esquema JSON de cada uma sai das anotações de tipo, então existe um único lugar para mudar.
"""
from __future__ import annotations

import inspect
import typing
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any, Callable

from pydantic import Field, ValidationError, create_model

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
        return _sem_titulos(self.modelo.model_json_schema())


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
