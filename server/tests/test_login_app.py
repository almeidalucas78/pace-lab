"""Login do app Android pelo navegador do celular (fase 9, etapa 8; ADR 0015): código de uso único com PKCE."""

import base64
import hashlib
import secrets
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from treino.api.app import app
from treino.auth import contas
from treino.auth.limite import limite
from treino.config import get_settings
from treino.db import AuthPending, session_scope

URL = "https://testserver"
SENHA = "corrida-no-parque-42"  # sintética
VERIFICADOR = "v" * 20 + secrets.token_urlsafe(32)


def _desafio(verificador: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).rstrip(b"=").decode()


@pytest.fixture
def cli(db, monkeypatch):
    monkeypatch.setenv("CADASTRO_EMAILS", "bia@exemplo.com")
    get_settings.cache_clear()
    limite.zera()
    with TestClient(app, base_url=URL) as c:
        r = c.post("/api/auth/cadastro", json={"email": "bia@exemplo.com", "senha": SENHA}, headers={"Origin": URL})
        assert r.status_code == 201, r.text
        yield c


def _codigo(cli, verificador: str = VERIFICADOR) -> str:
    r = cli.post("/api/auth/app/codigo", json={"desafio": _desafio(verificador)}, headers={"Origin": URL})
    assert r.status_code == 200, r.text
    return r.json()["codigo"]


def test_desafio_segue_o_exemplo_da_rfc_7636():
    # Apêndice B da RFC 7636.
    assert (
        contas.desafio_pkce("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk")
        == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    )


def test_app_troca_o_codigo_por_tokens_da_mesma_conta(cli):
    codigo = _codigo(cli)
    app_cli = TestClient(app, base_url=URL)  # o app não tem os cookies do navegador
    r = app_cli.post("/api/auth/app/trocar", json={"codigo": codigo, "verificador": VERIFICADOR})
    assert r.status_code == 200, r.text
    corpo = r.json()
    assert corpo["usuario"]["email"] == "bia@exemplo.com"
    assert corpo["acesso"].startswith("pla_") and corpo["renovacao"].startswith("plr_")
    assert "set-cookie" not in r.headers
    perfil = app_cli.get("/api/perfil", headers={"Authorization": f"Bearer {corpo['acesso']}"})
    assert perfil.status_code == 200
    # Renovação do app: token no corpo, sem cookie nem origem.
    r = app_cli.post("/api/auth/renovar", json={"renovacao": corpo["renovacao"]})
    assert r.status_code == 200 and r.json()["acesso"] != corpo["acesso"]


def test_codigo_e_de_uso_unico(cli):
    codigo = _codigo(cli)
    corpo = {"codigo": codigo, "verificador": VERIFICADOR}
    assert cli.post("/api/auth/app/trocar", json=corpo).status_code == 200
    assert cli.post("/api/auth/app/trocar", json=corpo).status_code == 400


def test_verificador_errado_gasta_o_codigo(cli):
    codigo = _codigo(cli)
    outro = "x" * 43
    assert cli.post("/api/auth/app/trocar", json={"codigo": codigo, "verificador": outro}).status_code == 400
    # Quem interceptou o código e errou o verificador não deixa o código vivo para nova tentativa.
    assert cli.post("/api/auth/app/trocar", json={"codigo": codigo, "verificador": VERIFICADOR}).status_code == 400


def test_codigo_vencido_nao_vale(cli):
    codigo = _codigo(cli)
    with session_scope() as s:
        s.execute(update(AuthPending).values(expires_utc=contas.agora() - timedelta(seconds=1)))
    r = cli.post("/api/auth/app/trocar", json={"codigo": codigo, "verificador": VERIFICADOR})
    assert r.status_code == 400


def test_gerar_codigo_pede_login_e_a_origem_do_proprio_site(cli):
    desafio = {"desafio": _desafio(VERIFICADOR)}
    assert cli.post("/api/auth/app/codigo", json=desafio).status_code == 403  # cookie sem Origin: CSRF
    anonimo = TestClient(app, base_url=URL)
    assert anonimo.post("/api/auth/app/codigo", json=desafio, headers={"Origin": URL}).status_code == 401
    r = cli.post("/api/auth/app/codigo", json={"desafio": "curto"}, headers={"Origin": URL})
    assert r.status_code == 422


def test_tentativas_demais_de_troca_esperam(cli):
    for _ in range(5):  # o mesmo limite do login por senha: 5 falhas em 15 min
        r = cli.post("/api/auth/app/trocar", json={"codigo": "chute", "verificador": VERIFICADOR})
        assert r.status_code == 400
    r = cli.post("/api/auth/app/trocar", json={"codigo": "chute", "verificador": VERIFICADOR})
    assert r.status_code == 429
