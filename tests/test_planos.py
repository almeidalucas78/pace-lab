from datetime import date

import pytest

from test_ia import db  # noqa: F401  (fixture: corrida em 20/10 com duplicata e caminhada em 18/10)
from treino import services
from treino.config import get_settings
from treino.db import session_scope
from treino.db.models import TrainingPlan

D = lambda dia: date(2026, 10, dia)


def sessoes_base():
    return [
        {"day": D(20), "sport": "run", "kind": "rodagem", "target_distance_km": 2, "target_hr_zone": "z2"},
        {"day": D(21), "sport": "rest", "kind": "descanso"},
        {"day": D(22), "sport": "run", "kind": "ritmo", "target_pace_min_s_km": 300, "target_pace_max_s_km": 320},
    ]


def criar(s, **kw):
    return services.create_plan(s, get_settings(), kw.pop("title", "Teste"), D(19), D(25),
                                kw.pop("sessions", sessoes_base()), **kw)


def test_aderencia_com_dados_do_banco(db):
    with session_scope() as s:
        plano = criar(s, goal="10 km")
        rep = services.plan_adherence(s, get_settings(), today=D(26))
    assert plano["status"] == "ativo" and [x["dia_semana"] for x in plano["sessoes"]] == ["ter", "qua", "qui"]
    assert plano["sessoes"][2]["ritmo"] == "5:00/km a 5:20/km"
    st = {l["dia"]: l["status"] for l in rep["sessoes"]}
    assert st == {"2026-10-20": "feita", "2026-10-21": "descanso", "2026-10-22": "perdida"}
    feita = rep["sessoes"][0]
    assert feita["comparacao"]["distancia"]["pct"] == 100
    assert feita["comparacao"]["zona_fc"]["pct_acima"] == 100   # FC 150 com FC máx 190 = z3, acima da z2
    assert feita["no_alvo"] is False
    assert rep["extras"] == []                                  # a duplicata não aparece como extra
    assert rep["resumo"]["pct_feitas"] == 50


def test_plano_novo_substitui_o_ativo(db):
    with session_scope() as s:
        p1 = criar(s, title="Bloco 1")
        p2 = criar(s, title="Bloco 2")
        antigo = s.get(TrainingPlan, p1["id"])
        assert antigo.status == "substituido" and antigo.replaced_by == p2["id"]
        assert services.active_plan(s).id == p2["id"]
        assert [p["titulo"] for p in services.list_plans(s, get_settings())] == ["Bloco 2", "Bloco 1"]


def test_ajustes_pontuais_e_validacoes(db):
    with session_scope() as s:
        plano = criar(s)
        sid = plano["sessoes"][2]["id"]
        movida = services.update_session(s, get_settings(), sid, {"day": D(23), "target_pace_max_s_km": None})
        assert movida["dia"] == "2026-10-23" and movida["ritmo"] == "5:00/km a -"
        assert services.update_session(s, get_settings(), sid, {}, cancel=True)["status"] == "cancelada"
        nova = services.add_session(s, get_settings(), None, {"day": D(25), "sport": "run", "kind": "longao",
                                                               "target_distance_km": 12})
        assert nova["tipo"] == "longao"
        with pytest.raises(ValueError, match="fora do plano"):
            services.update_session(s, get_settings(), sid, {"day": D(30)})
        with pytest.raises(ValueError, match="invertida"):
            services.add_session(s, get_settings(), None, {"day": D(24), "sport": "run", "kind": "ritmo",
                                                           "target_pace_min_s_km": 330, "target_pace_max_s_km": 300})
        with pytest.raises(ValueError, match="tipo inválido"):
            services.add_session(s, get_settings(), None, {"day": D(24), "sport": "run", "kind": "fartlek"})
        with pytest.raises(ValueError, match="fim do plano"):
            services.create_plan(s, get_settings(), "x", D(25), D(19), sessoes_base())


def test_arquivar_plano(db):
    with session_scope() as s:
        pid = criar(s)["id"]
        assert services.archive_plan(s, get_settings(), None)["status"] == "arquivado"
        assert services.active_plan(s) is None
        assert services.get_plan(s, pid).status == "arquivado"   # continua consultável pelo id
        with pytest.raises(ValueError, match="nenhum plano ativo"):
            services.archive_plan(s, get_settings(), None)


def test_ritmo_em_texto():
    assert services.parse_pace("5:30") == 330 and services.parse_pace("4:05/km") == 245
    assert services.parse_pace(None) is None
    with pytest.raises(ValueError):
        services.parse_pace("530")
    with pytest.raises(ValueError):
        services.parse_pace("0:30")


def test_api_e_cli_de_planos(db):
    from fastapi.testclient import TestClient
    from typer.testing import CliRunner

    from treino.api.app import app
    from treino.cli import app as cli

    h = {"Authorization": "Bearer teste"}
    with TestClient(app) as c:
        assert c.get("/planos/ativo", headers=h).status_code == 404
        with session_scope() as s:
            pid = criar(s)["id"]
        assert c.get("/planos", headers=h).json()[0]["id"] == pid
        assert len(c.get("/planos/ativo", headers=h).json()["sessoes"]) == 3
        assert "resumo" in c.get(f"/planos/{pid}/aderencia", headers=h).json()
        assert c.get("/planos/999", headers=h).status_code == 404
    out = CliRunner().invoke(cli, ["plano"])
    assert out.exit_code == 0 and "Teste (2026-10-19 a 2026-10-25, ativo)" in out.output
