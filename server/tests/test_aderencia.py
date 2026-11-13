from datetime import date

from treino.core.aderencia import Sessao, Treino, aderencia

SEG = date(2026, 10, 12)  # segunda-feira
D = lambda n: date(2026, 10, 12 + n)


def run(id, dia, km=8.0, minutos=45.0, pace=None, zones=None, sport="run"):
    return Treino(
        id=id,
        day=dia,
        sport=sport,
        distance_km=km,
        duration_min=minutos,
        pace_s_km=pace or (minutos * 60 / km if km else None),
        zones_s=zones or {},
    )


def status(r):
    return {l["sessao_id"]: l["status"] for l in r["sessoes"]}


def test_casamento_mesmo_dia_dia_vizinho_perdida_e_extra():
    sessoes = [
        Sessao(1, D(0), "run", "rodagem"),
        Sessao(2, D(2), "run", "rodagem"),
        Sessao(3, D(4), "run", "ritmo"),
        Sessao(4, D(5), "rest", "descanso"),
        Sessao(5, D(6), "run", "longao", status="cancelada"),
    ]
    # 11: dia seguinte da sessão 2; 12: domingo, sessão cancelada e a 2 dias da sessão 3, então é extra
    treinos = [run(10, D(0)), run(11, D(3)), run(12, D(6))]
    r = aderencia(sessoes, treinos, D(0), D(6), hoje=D(7))
    st = status(r)
    assert st == {1: "feita", 2: "feita_outro_dia", 3: "perdida", 4: "descanso", 5: "cancelada"}
    assert [e["treino_id"] for e in r["extras"]] == [12]
    assert r["resumo"]["pct_feitas"] == 67 and r["resumo"]["perdidas"] == 1
    assert r["semanas"][0]["planejadas"] == 3 and r["semanas"][0]["km_feitos"] == 24.0


def test_mesmo_dia_tem_prioridade_sobre_dia_vizinho():
    # o treino de terça pertence à sessão de terça, não à de segunda (que fica perdida)
    sessoes = [Sessao(1, D(0), "run", "rodagem"), Sessao(2, D(1), "run", "rodagem")]
    r = aderencia(sessoes, [run(10, D(1))], D(0), D(1), hoje=D(5))
    assert status(r) == {1: "perdida", 2: "feita"}


def test_esporte_diferente_nao_casa_e_futuras():
    sessoes = [
        Sessao(1, D(0), "strength", "musculacao"),
        Sessao(2, D(3), "run", "rodagem"),
        Sessao(3, D(4), "run", "rodagem"),
    ]
    treinos = [run(10, D(0)), run(11, D(0), sport="strength", km=None, minutos=60)]
    r = aderencia(sessoes, treinos, D(0), D(6), hoje=D(3))
    assert status(r) == {1: "feita", 2: "pendente_hoje", 3: "futura"}
    assert r["resumo"]["futuras"] == 2 and [e["treino_id"] for e in r["extras"]] == [10]


def test_metas_de_distancia_ritmo_e_zona():
    s = Sessao(
        1,
        D(0),
        "run",
        "rodagem",
        target_distance_km=8,
        target_pace_min_s_km=330,
        target_pace_max_s_km=350,
        target_hr_zone="z2",
    )
    zonas = {"z0": 0, "z1": 60, "z2": 1800, "z3": 540, "z4": 0, "z5": 0}
    r = aderencia([s], [run(10, D(0), km=8.2, minutos=46, pace=340, zones=zonas)], D(0), D(0), hoje=D(1))
    (linha,) = r["sessoes"]
    c = linha["comparacao"]
    assert c["distancia"]["pct"] == 102 and c["ritmo"]["situacao"] == "dentro"
    assert c["ritmo"]["alvo"] == "5:30/km a 5:50/km"
    assert c["zona_fc"] == {"alvo": "z2", "pct_na_zona": 75, "pct_acima": 22, "pct_abaixo": 2}
    assert linha["no_alvo"] is False  # 22% acima da zona passa do limite de 20%

    rapido = aderencia([s], [run(10, D(0), km=8, minutos=40, pace=300)], D(0), D(0), hoje=D(1))
    assert rapido["sessoes"][0]["comparacao"]["ritmo"]["situacao"] == "mais_rapido"


def test_sessao_sem_meta_nao_tem_no_alvo():
    r = aderencia([Sessao(1, D(0), "run", "regenerativo")], [run(10, D(0))], D(0), D(0), hoje=D(1))
    assert "no_alvo" not in r["sessoes"][0] and "comparacao" not in r["sessoes"][0]
