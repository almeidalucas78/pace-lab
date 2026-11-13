"""Atualização do app Android pelo próprio app: o PC publica o APK e a versão (fase 7, etapa 4b)."""

import json

import pytest
from fastapi.testclient import TestClient

from treino import services
from treino.api.app import app
from treino.config import get_settings

H = {"Authorization": "Bearer teste"}


@pytest.fixture
def pastas(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path.as_posix()}/v.db")
    monkeypatch.setenv("API_TOKEN", "teste")
    monkeypatch.setenv("PASTA_APP", str(tmp_path / "app"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


def build(pasta, codigo, conteudo=b"apk falso", app_id="app.pacelab"):
    """Imita a saída do Gradle: o APK e o output-metadata.json ao lado."""
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "app-debug.apk").write_bytes(conteudo)
    (pasta / "output-metadata.json").write_text(
        json.dumps(
            {
                "version": 3,
                "applicationId": app_id,
                "variantName": "debug",
                "elements": [
                    {
                        "type": "SINGLE",
                        "versionCode": codigo,
                        "versionName": f"0.7.{codigo}",
                        "outputFile": "app-debug.apk",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return pasta


def test_sem_versao_publicada(pastas):
    with TestClient(app) as c:
        assert c.get("/api/app/versao", headers=H).json() == {"codigo": None}
        assert c.get("/api/app/apk", headers=H).status_code == 404
        assert c.get("/api/app/versao").status_code == 401


def test_publicar_e_baixar(pastas):
    info = services.publish_app(get_settings(), build(pastas / "b1", 5, b"versao 5"))
    assert info["codigo"] == 5 and info["nome"] == "0.7.5" and info["tamanho"] == 8
    with TestClient(app) as c:
        assert c.get("/api/app/versao", headers=H).json()["codigo"] == 5
        r = c.get("/api/app/apk", headers=H)
        assert r.status_code == 200 and r.content == b"versao 5"
        assert r.headers["content-type"] == "application/vnd.android.package-archive"
        assert c.get("/api/app/apk").status_code == 401  # o APK também exige o token


def test_nao_publica_versao_menor_nem_build_de_outro_app(pastas):
    services.publish_app(get_settings(), build(pastas / "b1", 5))
    with pytest.raises(ValueError, match="menor"):
        services.publish_app(get_settings(), build(pastas / "b2", 4))
    with pytest.raises(ValueError, match="Pace Lab"):
        services.publish_app(get_settings(), build(pastas / "b3", 9, app_id="outro.app"))
    with pytest.raises(FileNotFoundError):
        services.publish_app(get_settings(), pastas / "vazia")
    assert services.app_version(get_settings())["codigo"] == 5
