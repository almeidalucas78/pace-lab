from fastapi.testclient import TestClient

from test_ia import db  # noqa: F401
from treino.api import app as app_mod
from treino.api.app import app

H = {"Authorization": "Bearer teste"}


def test_rotas_da_api_ficam_em_api(db):
    with TestClient(app) as c:
        assert c.get("/api/health").json() == {"status": "ok"}
        assert c.get("/api/perfil", headers=H).json()["fc_max"] == 190
        assert "hoje" in c.get("/api/carga/atual", headers=H).json()
        assert len(c.get("/api/activities?limit=5", headers=H).json()) == 3
        assert c.get("/api/perfil").status_code == 401
        assert c.get("/api/nao-existe", headers=H).status_code == 404
        assert c.get("/api/openapi.json").status_code == 200


def test_painel_servido_na_raiz(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>painel</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "segredo.txt").write_text("nao", encoding="utf-8")
    monkeypatch.setattr(app_mod, "PAINEL", dist)
    with TestClient(app) as c:
        assert c.get("/").text == "<html>painel</html>"
        assert c.get("/treinos/356").text == "<html>painel</html>"     # rota do React Router
        assert c.get("/assets/app.js").text == "console.log(1)"
        assert "nao" not in c.get("/../segredo.txt").text
        assert "nao" not in c.get("/%2e%2e/segredo.txt").text


def test_sem_build_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(app_mod, "PAINEL", tmp_path / "nao-existe")
    with TestClient(app) as c:
        r = c.get("/")
        assert r.status_code == 404 and "npm run build" in r.json()["aviso"]


def test_aviso_de_porta_ocupada():
    import socket

    from treino.cli import _porta_ocupada
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        porta = s.getsockname()[1]
        assert _porta_ocupada("127.0.0.1", porta) == "outro programa está usando essa porta."
    assert _porta_ocupada("127.0.0.1", porta) is None
