"""Rotas que o painel usa para a conta (fase 9, etapa 7): opções de login, ajustes e envio do export do Strava."""

import gzip
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from treino.api.app import app
from treino.auth.limite import limite
from treino.config import get_settings
from treino.ingest import strava_export
from treino.ingest.files import ArquivoGrande, gunzip

from test_basico import make_csv, make_gpx

A = {"Authorization": "Bearer teste"}  # API_TOKEN antigo = conta do dono
URL = "https://testserver"
SENHA = "corrida-no-parque-42"  # sintética


def _export(gpx_n: int = 400) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(
            "export_1/activities.csv",
            make_csv(
                [
                    '20,"21 de out. de 2026, 07:00:00",Rodagem,Corrida,400,"1,20",150,activities/20.gpx.gz,400.0,400.0,1200.0,10.0,80.0',
                    '21,"19 de out. de 2026, 07:00:00",Passeio,Caminhada,600,"0,5",110,,600.0,600.0,500.0,5.0,40.0',
                ]
            ),
        )
        z.writestr("export_1/activities/20.gpx.gz", gzip.compress(make_gpx(n=gpx_n)))
    return buf.getvalue()


@pytest.fixture
def cli(db, monkeypatch):
    monkeypatch.setenv("CADASTRO_EMAILS", "bia@exemplo.com")
    get_settings.cache_clear()
    limite.zera()
    with TestClient(app, base_url=URL) as c:
        tok = c.post("/api/auth/cadastro", json={"email": "bia@exemplo.com", "senha": SENHA, "cliente": "app"}).json()
        c.b = {"Authorization": f"Bearer {tok['acesso']}"}  # type: ignore[attr-defined]
        yield c


def test_opcoes_e_publica_e_diz_se_o_google_esta_ligado(cli):
    assert cli.get("/api/auth/opcoes").json() == {"google": False}


def test_ajustes_mudam_so_a_conta_de_quem_chama(cli):
    r = cli.post("/api/perfil/ajustes", json={"fc_max": 185, "fc_repouso": 52, "fuso": "Europe/Lisbon"}, headers=cli.b)
    assert r.status_code == 200, r.text
    p = r.json()
    assert (p["fc_max"], p["fc_max_origem"], p["fc_repouso"], p["fuso"]) == (185, "configurada", 52, "Europe/Lisbon")
    assert cli.get("/api/perfil", headers=cli.b).json()["fuso"] == "Europe/Lisbon"
    dono = cli.get("/api/perfil", headers=A).json()
    assert (dono["fc_max"], dono["fuso"]) == (190, "America/Sao_Paulo")
    # 0 apaga: a FC máxima volta a ser estimada (a conta B não tem treinos, então fica sem valor)
    p = cli.post("/api/perfil/ajustes", json={"fc_max": 0, "fc_repouso": 0}, headers=cli.b).json()
    assert p["fc_max_origem"] != "configurada"
    assert (p["fc_repouso"], p["fuso"]) == (None, "Europe/Lisbon")


@pytest.mark.parametrize(
    "corpo", [{"fc_max": 250}, {"fc_max": 90}, {"fc_repouso": 10}, {"fuso": "Lua/Mar_da_Tranquilidade"}]
)
def test_ajustes_fora_do_razoavel_sao_recusados(cli, corpo):
    r = cli.post("/api/perfil/ajustes", json=corpo, headers=cli.b)
    assert r.status_code == 422
    assert cli.get("/api/perfil", headers=cli.b).json()["fuso"] == "America/Sao_Paulo"


def test_export_enviado_pelo_painel_vai_para_a_conta_de_quem_enviou(cli):
    r = cli.post("/api/importar/strava", content=_export(), headers=cli.b | {"Content-Type": "application/zip"})
    assert r.status_code == 200, r.text
    rep = r.json()
    assert (rep["atividades"], rep["novas"], rep["arquivo_ok"]) == (2, 2, 1)
    assert "fc_max_origem" in rep
    assert len(cli.get("/api/activities", headers=cli.b).json()) == 2
    assert len(cli.get("/api/activities", headers=A).json()) == 3  # o dono continua com os dele
    # Mandar de novo só atualiza.
    rep = cli.post("/api/importar/strava", content=_export(), headers=cli.b).json()
    assert (rep.get("novas", 0), rep["atualizadas"]) == (0, 2)
    assert len(cli.get("/api/activities", headers=cli.b).json()) == 2


def test_export_invalido_e_recusado(cli):
    r = cli.post("/api/importar/strava", content=b"isto nao e zip", headers=cli.b)
    assert r.status_code == 400
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("outra-coisa.txt", "oi")
    r = cli.post("/api/importar/strava", content=buf.getvalue(), headers=cli.b)
    assert r.status_code == 400
    assert "activities.csv" in r.json()["detail"]
    r = cli.post("/api/importar/strava", content=b"x", headers=cli.b | {"Content-Length": str(2 * 1024**3)})
    assert r.status_code == 413


def test_export_por_cookie_pede_a_origem_do_proprio_site(cli):
    cli.post("/api/auth/entrar", json={"email": "bia@exemplo.com", "senha": SENHA})
    assert cli.post("/api/importar/strava", content=_export()).status_code == 403
    r = cli.post("/api/importar/strava", content=_export(), headers={"Origin": URL})
    assert r.status_code == 200, r.text
    assert r.json()["novas"] == 2


def test_arquivo_que_descompacta_demais_nao_entra(cli, monkeypatch):
    with pytest.raises(ArquivoGrande):
        gunzip(gzip.compress(b"0" * 5000), limite=1000)
    assert gunzip(gzip.compress(b"abc"), limite=1000) == b"abc"
    # Dentro do zip, o arquivo grande demais vira erro daquele treino, sem derrubar a importação.
    monkeypatch.setattr(strava_export, "LIMITE_DESCOMPACTADO", 1000)
    rep = cli.post("/api/importar/strava", content=_export(gpx_n=400), headers=cli.b).json()
    assert (rep["atividades"], rep["arquivo_erro"]) == (2, 1)
