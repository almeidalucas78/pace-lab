"""Dados por usuário (fase 9, etapa 3): a conta B não lê nem altera nada da conta A, pela API e pelas ferramentas."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from treino import services
from treino.api.app import app
from treino.auth.limite import limite
from treino.config import get_settings
from treino.conta import do_dono, do_usuario
from treino.db import session_scope
from treino.db.models import (
    Activity,
    Conversation,
    DailyLoad,
    PlannedSession,
    Sensation,
    SyncState,
    TrainingPlan,
    User,
)
from treino.ia.ferramentas import executar

A = {"Authorization": "Bearer teste"}  # API_TOKEN antigo = conta do dono (A), que tem os treinos sintéticos
URL = "https://testserver"
SENHA = "corrida-no-parque-42"  # sintética


@pytest.fixture
def cli(db, monkeypatch):
    monkeypatch.setenv("CADASTRO_EMAILS", "bia@exemplo.com")
    get_settings.cache_clear()
    limite.zera()
    with TestClient(app, base_url=URL) as c:
        tok = c.post(
            "/api/auth/cadastro",
            json={"email": "bia@exemplo.com", "senha": SENHA, "cliente": "app"},
        ).json()
        c.b = {"Authorization": f"Bearer {tok['acesso']}"}  # type: ignore[attr-defined]
        yield c


def _plano(c, h):
    with session_scope() as s:
        conta = do_dono(s) if h is A else do_usuario(s, _id_b(s))
        hoje = datetime.now(conta.tz).date()
        sessoes = [{"day": hoje, "sport": "run", "kind": "rodagem", "target_distance_km": 5}]
        return services.create_plan(s, conta, "Plano", hoje, hoje + timedelta(days=6), sessoes)["id"]


def _id_b(s) -> int:
    return s.scalar(select(User.id).where(User.email == "bia@exemplo.com"))


def test_conta_nova_comeca_vazia_e_nao_ve_os_treinos_do_dono(cli):
    a_treinos = cli.get("/api/activities", headers=A).json()
    assert len(a_treinos) == 3
    aid = a_treinos[0]["id"]
    b = cli.b
    assert cli.get("/api/activities", headers=b).json() == []
    assert cli.get(f"/api/activities/{aid}", headers=b).status_code == 404
    assert cli.get(f"/api/activities/{aid}/samples", headers=b).status_code == 404
    assert cli.get("/api/overview", headers=b).json()["por_esporte"] == {}
    assert all(w["treinos"] == 0 for w in cli.get("/api/weeks?n=104", headers=b).json())
    assert cli.get("/api/load", headers=b).json() == []
    assert cli.get("/api/perfil", headers=b).json()["historico"]["por_esporte"] == {}
    assert cli.get("/api/carga/atual", headers=b).json() == {"aviso": "sem dados de carga"}
    assert cli.get("/api/sync/status", headers=b).json()["fontes"] == []
    # O dono continua vendo tudo.
    assert cli.get(f"/api/activities/{aid}", headers=A).status_code == 200
    assert cli.get(f"/api/activities/{aid}/samples", headers=A).status_code == 200


def test_planos_e_sensacoes_ficam_com_o_dono(cli):
    pa = _plano(cli, A)
    assert cli.get("/api/planos", headers=cli.b).json() == []
    assert cli.get(f"/api/planos/{pa}", headers=cli.b).status_code == 404
    assert cli.get(f"/api/planos/{pa}/aderencia", headers=cli.b).status_code == 404
    assert cli.get("/api/planos/ativo", headers=cli.b).status_code == 404
    # B cria o plano dele: o de A continua ativo.
    pb = _plano(cli, cli.b)
    assert cli.get("/api/planos/ativo", headers=A).json()["id"] == pa
    assert cli.get("/api/planos/ativo", headers=cli.b).json()["id"] == pb
    with session_scope() as s:
        a = do_dono(s)
        services.add_sensation(s, a, "joelho doendo", rpe=7)
        sid = s.scalar(select(PlannedSession.id).where(PlannedSession.plan_id == pa))
        b = do_usuario(s, _id_b(s))
        aid = s.scalar(select(Activity.id).where(Activity.user_id == a.user_id).limit(1))
        with pytest.raises(ValueError):
            services.update_session(s, b, sid, {}, cancel=True)  # sessão do plano de A
        with pytest.raises(ValueError):
            services.add_sensation(s, b, "não é meu", activity_id=aid)  # treino de A
    assert cli.get("/api/sensacoes", headers=cli.b).json() == []
    assert len(cli.get("/api/sensacoes", headers=A).json()) == 1


def test_conversas_separadas(cli, monkeypatch):
    from treino.ia import chat as chat_mod
    from treino.ia.provedores import Resposta

    class Falso:
        async def responder(self, mensagem, historico, sessao):
            return Resposta(texto="ok")

    monkeypatch.setattr(chat_mod, "criar_provedor", lambda *_: Falso())
    ca = cli.post("/api/chat", json={"mensagem": "conversa de A"}, headers=A).json()["conversa_id"]
    assert cli.get("/api/chat/conversas", headers=cli.b).json() == []
    assert cli.get(f"/api/chat/conversas/{ca}", headers=cli.b).status_code == 404
    # B não consegue escrever na conversa de A.
    r = cli.post("/api/chat", json={"mensagem": "entrando", "conversa_id": ca}, headers=cli.b)
    assert r.status_code == 502 and "não existe" in r.json()["detail"]
    cb = cli.post("/api/chat", json={"mensagem": "conversa de B"}, headers=cli.b).json()["conversa_id"]
    assert [c["id"] for c in cli.get("/api/chat/conversas", headers=cli.b).json()] == [cb]
    assert [c["id"] for c in cli.get("/api/chat/conversas", headers=A).json()] == [ca]


def test_ferramentas_da_ia_respeitam_a_conta(cli):
    with session_scope() as s:
        a, b = do_dono(s), do_usuario(s, _id_b(s))
        aid = s.scalar(select(Activity.id).where(Activity.user_id == a.user_id).limit(1))
    assert executar("listar_treinos", {"esporte": "todos"}, b) == []
    assert executar("ultimo_treino", {}, b) == {"aviso": "nenhum treino encontrado"}
    assert "erro" in executar("detalhe_treino", {"treino_id": aid}, b)
    assert "erro" in executar("registrar_sensacao", {"texto": "x", "treino_id": aid}, b)
    assert executar("registrar_sensacao", {"texto": "dormi mal"}, b)["texto"] == "dormi mal"
    assert executar("ver_sensacoes", {}, a) == []  # a sensação de B não aparece para A
    # Sem conta marcada (MCP local no PC), as ferramentas usam a conta do dono.
    assert len(executar("listar_treinos", {"esporte": "todos"})) == 2  # sem a duplicata
    assert executar("detalhe_treino", {"treino_id": aid})["id"] == aid


def _lote(id_, inicio):
    return {
        "fonte": "samsung_health",
        "treinos": [
            {
                "id": id_,
                "tipo": "RUNNING",
                "inicio": inicio.isoformat(),
                "fim": (inicio + timedelta(minutes=30)).isoformat(),
                "distancia_m": 5000,
            }
        ],
    }


def test_mesmo_treino_da_fonte_em_duas_contas_e_carga_separada(cli):
    inicio = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
    assert cli.post("/api/saude/treinos", json=_lote("uid-1", inicio), headers=A).status_code == 200
    assert cli.post("/api/saude/treinos", json=_lote("uid-1", inicio), headers=cli.b).status_code == 200
    # B apaga o treino no celular dele: o de A fica.
    lote = {"fonte": "samsung_health", "treinos": [], "apagados": ["uid-1"]}
    assert cli.post("/api/saude/treinos", json=lote, headers=cli.b).json()["apagados"] == 1
    with session_scope() as s:
        a, b = do_dono(s), do_usuario(s, _id_b(s))
        q = select(func.count()).select_from(Activity).where(Activity.source_id == "uid-1")
        assert s.scalar(q.where(Activity.user_id == a.user_id)) == 1
        assert s.scalar(q.where(Activity.user_id == b.user_id)) == 0
        assert s.get(SyncState, (a.user_id, "samsung_health")) is not None
        assert s.get(SyncState, (b.user_id, "samsung_health")) is not None
        # Recalcular a conta B não mexe na carga de A.
        dias_a = s.scalar(select(func.count()).select_from(DailyLoad).where(DailyLoad.user_id == a.user_id))
        services.recompute(s, b)
        assert s.scalar(select(func.count()).select_from(DailyLoad).where(DailyLoad.user_id == a.user_id)) == dias_a
    assert cli.get("/api/activities", headers=cli.b).json() == []


def test_todos_os_registros_tem_dono(cli):
    with session_scope() as s:
        for modelo in (Activity, Sensation, Conversation, TrainingPlan, SyncState, DailyLoad):
            assert s.scalar(select(func.count()).select_from(modelo).where(modelo.user_id.is_(None))) == 0


def test_conta_provisoria_e_assumida_pelo_dono(db):
    from treino.auth import contas, senhas

    with session_scope() as s:
        dono = s.get(User, do_dono(s).user_id)
        dono.email = contas.CONTA_PROVISORIA  # como a migração deixa um banco antigo sem contas
    with session_scope() as s:
        u = contas.assumir_provisoria(s, "Lucas@Exemplo.com", SENHA, "Lucas")
        assert u is not None and u.email == "lucas@exemplo.com" and senhas.confere(u.password_hash, SENHA)
        assert s.scalar(select(func.count()).select_from(Activity).where(Activity.user_id == u.id)) == 3
    with session_scope() as s:
        assert contas.assumir_provisoria(s, "outro@exemplo.com", SENHA) is None
