import asyncio
import gzip
import zipfile

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from test_basico import make_csv, make_gpx
from treino import services
from treino.config import get_settings
from treino.db import init_db, session_scope
from treino.db.session import get_engine
from treino.ia import chat as chat_mod
from treino.ia.chat import conversar
from treino.ia.ferramentas import REGISTRO, executar
from treino.ia.mcp_server import criar_servidor
from treino.ia.provedores import ErroIA, Gemini, Resposta
from treino.ingest.strava_export import import_strava_export


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Banco temporário com duas corridas sintéticas (a segunda é duplicata da primeira) e uma caminhada."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path.as_posix()}/ia.db")
    monkeypatch.setenv("FC_MAX", "190")
    monkeypatch.setenv("API_TOKEN", "teste")
    get_settings.cache_clear()
    get_engine.cache_clear()
    init_db()
    zpath = tmp_path / "export.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("activities.csv", make_csv([
            '10,"20 de out. de 2026, 10:00:00",Corrida A,Corrida,700,"2,00",160,activities/10.gpx.gz,700.0,699.0,2000.0,86.0,150.0',
            '11,"20 de out. de 2026, 10:03:00",Corrida A copia,Corrida,700,"2,00",160,,700.0,699.0,2000.0,86.0,150.0',
            '12,"18 de out. de 2026, 10:00:00",Passeio,Caminhada,600,"0,5",120,,600.0,600.0,500.0,110.0,100.0',
        ]))
        z.writestr("activities/10.gpx.gz", gzip.compress(make_gpx(n=700)))
    with session_scope() as s:
        import_strava_export(s, zpath)
        services.recompute(s, get_settings())
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()


def test_esquemas_das_ferramentas():
    nomes = {f.nome for f in REGISTRO}
    assert {"ultimo_treino", "detalhe_treino", "resumo_semanas", "carga_atual", "registrar_sensacao"} <= nomes
    por_nome = {f.nome: f.schema for f in REGISTRO}
    assert "title" not in str(por_nome)
    assert por_nome["listar_treinos"]["properties"]["limite"]["maximum"] == 50
    assert por_nome["registrar_sensacao"]["required"] == ["texto"]
    assert por_nome["carga_atual"]["properties"] == {}


def test_ferramentas_devolvem_fichas(db):
    card = executar("ultimo_treino", {})
    assert card["nome"] == "Corrida A" and [p["km"] for p in card["parciais"]] == [1, 2]
    assert "observacoes_dados" not in card and card["sensacoes"] == []

    lista = executar("listar_treinos", {"esporte": "todos"})
    assert [t["nome"] for t in lista] == ["Corrida A", "Passeio"]          # duplicata fica de fora

    reg = executar("registrar_sensacao", {"texto": "pernas pesadas", "rpe": 7, "treino_id": card["id"]})
    assert reg["dia"] == "2026-10-20" and reg["rpe"] == 7
    assert executar("detalhe_treino", {"treino_id": card["id"]})["sensacoes"][0]["texto"] == "pernas pesadas"

    assert "erro" in executar("registrar_sensacao", {"texto": "x", "rpe": 11})
    assert "erro" in executar("detalhe_treino", {"treino_id": 999})
    assert "erro" in executar("nao_existe", {})
    perfil = executar("perfil_atleta", {})
    assert perfil["fc_max"] == 190 and perfil["zonas_fc"]["z5"] == "171 a 190 bpm"
    assert "hoje" in executar("carga_atual", {})


class ProvedorFalso:
    nome = "falso"

    def __init__(self):
        self.chamadas = []

    async def responder(self, mensagem, historico, sessao):
        self.chamadas.append((mensagem, list(historico), sessao))
        return Resposta(texto=f"resposta {len(self.chamadas)}", ferramentas=["ultimo_treino"], sessao="s1")


def test_chat_grava_e_retoma_conversa(db):
    falso = ProvedorFalso()
    r1 = asyncio.run(conversar("como foi meu treino?", provedor="claude", fabrica=lambda n, s: falso))
    r2 = asyncio.run(conversar("e a carga?", conversa_id=r1["conversa_id"], fabrica=lambda n, s: falso))
    assert r2["conversa_id"] == r1["conversa_id"] and r2["resposta"] == "resposta 2"
    msg, historico, sessao = falso.chamadas[1]
    assert historico == [("user", "como foi meu treino?"), ("assistant", "resposta 1")] and sessao == "s1"
    with session_scope() as s:
        conv = services.conversation_detail(s, get_settings(), r1["conversa_id"])
    assert conv["provedor"] == "claude" and len(conv["mensagens"]) == 4
    with pytest.raises(ErroIA):
        asyncio.run(conversar("oi", conversa_id=r1["conversa_id"], provedor="gemini", fabrica=lambda n, s: falso))


class GeminiFalso:
    """Imita client.aio.models.generate_content: primeiro pede uma ferramenta, depois responde."""

    def __init__(self):
        self.contents = []
        self.aio = self
        self.models = self

    async def generate_content(self, model, contents, config):
        self.contents.append(list(contents))
        if len(self.contents) == 1:
            part = types.Part(function_call=types.FunctionCall(id="c1", name="ultimo_treino", args={}))
        else:
            part = types.Part(text="Seu último treino foi bom.")
        return types.GenerateContentResponse(candidates=[types.Candidate(
            content=types.Content(role="model", parts=[part]))])


def test_gemini_executa_ferramentas_e_devolve_resultado(db):
    falso = GeminiFalso()
    r = asyncio.run(Gemini(get_settings(), client=falso).responder("e aí?", [("user", "oi"), ("assistant", "olá")], None))
    assert r.texto == "Seu último treino foi bom." and r.ferramentas == ["ultimo_treino"]
    ultimo = falso.contents[1][-1].parts[0].function_response
    assert ultimo.id == "c1" and ultimo.response["resultado"]["nome"] == "Corrida A"
    assert [c.role for c in falso.contents[0]] == ["user", "model", "user"]


def test_servidor_mcp_expoe_o_registro():
    tools = asyncio.run(criar_servidor().list_tools())
    assert sorted(t.name for t in tools) == sorted(f.nome for f in REGISTRO)


def test_api_de_chat(db, monkeypatch):
    falso = ProvedorFalso()
    monkeypatch.setattr(chat_mod, "criar_provedor", lambda n, s: falso)
    from treino.api.app import app
    with TestClient(app) as c:
        h = {"Authorization": "Bearer teste"}
        r = c.post("/chat", json={"mensagem": "oi"}, headers=h)
        assert r.status_code == 200 and r.json()["resposta"] == "resposta 1"
        assert c.get("/chat/conversas", headers=h).json()[0]["titulo"] == "oi"
        assert c.post("/chat", json={"mensagem": "oi"}).status_code == 401

        def falha(n, s):
            raise ErroIA("sem cota")
        monkeypatch.setattr(chat_mod, "criar_provedor", falha)
        r = c.post("/chat", json={"mensagem": "oi"}, headers=h)
        assert r.status_code == 502 and r.json()["detail"] == "sem cota"


def test_ferramentas_de_plano(db):
    plano = executar("salvar_plano", {
        "titulo": "Base 10 km", "inicio": "2026-10-19", "fim": "2026-10-25", "objetivo": "10 km",
        "sessoes": [
            {"dia": "2026-10-20", "esporte": "run", "tipo": "rodagem", "distancia_km": 2, "ritmo_min": "5:30",
             "ritmo_max": "6:00"},
            {"dia": "2026-10-21", "esporte": "rest", "tipo": "descanso"},
            {"dia": "2026-10-23", "esporte": "run", "tipo": "intervalado", "duracao_min": 40, "esforco": 8},
        ]})
    assert plano["status"] == "ativo" and plano["sessoes"][0]["ritmo"] == "5:30/km a 6:00/km"
    sid = plano["sessoes"][0]["id"]

    alterada = executar("alterar_sessao", {"sessao_id": sid, "distancia_km": 3, "limpar": ["ritmo_max"]})
    assert alterada["distancia_km"] == 3 and alterada["ritmo"] == "5:30/km a -"
    assert executar("adicionar_sessao", {"sessao": {"dia": "2026-10-25", "esporte": "run", "tipo": "longao",
                                                    "distancia_km": 12}})["tipo"] == "longao"
    assert len(executar("plano_atual", {})["sessoes"]) == 4

    rep = executar("aderencia_plano", {})
    assert rep["plano"]["titulo"] == "Base 10 km"
    assert {l["sessao_id"]: l["status"] for l in rep["sessoes"]}[sid] == "feita"
    assert executar("listar_planos", {})[0]["titulo"] == "Base 10 km"

    assert "erro" in executar("salvar_plano", {"titulo": "x", "inicio": "2026-10-19", "fim": "2026-10-25",
                                               "sessoes": [{"dia": "2026-11-01", "esporte": "run", "tipo": "rodagem"}]})
    assert "erro" in executar("alterar_sessao", {"sessao_id": sid, "ritmo_min": "530"})
    assert "erro" in executar("adicionar_sessao", {"sessao": {"dia": "2026-10-24", "esporte": "run", "tipo": "fartlek"}})


def test_plano_criado_no_chat_fica_ligado_a_conversa(db):
    class CriaPlano(ProvedorFalso):
        async def responder(self, mensagem, historico, sessao):
            executar("salvar_plano", {"titulo": "Do chat", "inicio": "2026-10-19", "fim": "2026-10-25",
                                      "sessoes": [{"dia": "2026-10-20", "esporte": "run", "tipo": "rodagem"}]})
            return await super().responder(mensagem, historico, sessao)

    r = asyncio.run(conversar("pode salvar", provedor="claude", fabrica=lambda n, s: CriaPlano()))
    assert executar("plano_atual", {})["conversa_id"] == r["conversa_id"]


class GeminiSobrecarregado(GeminiFalso):
    """O modelo principal responde 503; os outros funcionam como o GeminiFalso."""

    def __init__(self, falha_depois_de_ferramenta=False):
        super().__init__()
        self.modelos, self.falha_depois = [], falha_depois_de_ferramenta

    async def generate_content(self, model, contents, config):
        from google.genai import errors
        self.modelos.append(model)
        if model == "principal" and (not self.falha_depois or len(self.modelos) > 1):
            raise errors.ServerError(503, {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}})
        return await super().generate_content(model, contents, config)


def test_gemini_usa_modelo_de_reserva_quando_o_principal_esta_sobrecarregado(db):
    settings = get_settings().model_copy(update={"gemini_modelo": "principal", "gemini_modelo_reserva": "reserva"})
    falso = GeminiSobrecarregado()
    r = asyncio.run(Gemini(settings, client=falso).responder("e aí?", [], None))
    assert falso.modelos == ["principal", "reserva", "reserva"] and r.meta["modelo"] == "reserva"
    assert r.meta["reserva_por"] == "principal: 503" and r.ferramentas == ["ultimo_treino"]

    # depois de uma ferramenta já ter rodado, não repete a resposta em outro modelo
    falso = GeminiSobrecarregado(falha_depois_de_ferramenta=True)
    with pytest.raises(ErroIA, match="503"):
        asyncio.run(Gemini(settings, client=falso).responder("e aí?", [], None))
    assert falso.modelos == ["principal", "principal"]
