"""Contas e login (fase 9, etapa 2): senha, sessões com rotação, CSRF, limite de tentativas e Google simulado."""

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from treino.api.app import app
from treino.auth import contas, senhas
from treino.auth.limite import MAX_POR_EMAIL_IP, limite
from treino.config import get_settings

URL = "https://testserver"
ORIGEM = {"Origin": URL}
SENHA = "corrida-no-parque-42"


@pytest.fixture
def cli(db, monkeypatch):
    monkeypatch.setenv("CADASTRO_EMAILS", "ana@exemplo.com, bia@exemplo.com")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cliente-teste")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "segredo-teste")
    monkeypatch.setenv("URL_PUBLICA", URL)
    get_settings.cache_clear()
    limite.zera()
    with TestClient(app, base_url=URL) as c:
        yield c
    limite.zera()


def _cadastra(c: TestClient, email="ana@exemplo.com", senha=SENHA, cliente="web"):
    return c.post("/api/auth/cadastro", json={"email": email, "senha": senha, "nome": "Ana", "cliente": cliente})


def test_regras_da_senha():
    assert "8 caracteres" in senhas.problema("curta1")
    assert "mais usadas" in senhas.problema("password1")
    assert "mais usadas" in senhas.problema("PassWord1")  # sem diferença de maiúsculas
    assert senhas.problema("x" * 129) is not None
    assert senhas.problema(SENHA) is None
    h = senhas.gerar_hash(SENHA)
    assert h.startswith("$argon2id$") and SENHA not in h
    assert senhas.confere(h, SENHA) and not senhas.confere(h, "outra-senha-qualquer")
    assert not senhas.confere(None, SENHA)


def test_cadastro_fechado_pela_lista(cli):
    r = _cadastra(cli, email="intrusa@exemplo.com")
    assert r.status_code == 403 and "cadastro fechado" in r.json()["detail"]
    assert _cadastra(cli, senha="12345678").status_code == 400  # senha comum
    r = _cadastra(cli, email=" Ana@Exemplo.com ")
    assert r.status_code == 201 and r.json()["usuario"]["email"] == "ana@exemplo.com"
    assert "pl_acesso" in cli.cookies and SENHA not in r.text
    assert _cadastra(cli).status_code == 409


def test_cookie_do_painel_abre_a_api_e_sair_derruba(cli):
    _cadastra(cli)
    assert cli.get("/api/auth/eu").json()["email"] == "ana@exemplo.com"
    assert cli.get("/api/perfil").status_code == 200
    # Gravar com cookie exige a origem do próprio site (CSRF).
    assert cli.post("/api/auth/sair").status_code == 403
    assert cli.post("/api/auth/sair", headers={"Origin": "https://malicioso.example"}).status_code == 403
    acesso = cli.cookies["pl_acesso"]
    assert cli.post("/api/auth/sair", headers=ORIGEM).status_code == 200
    assert "pl_acesso" not in cli.cookies
    assert cli.get("/api/perfil", headers={"Authorization": f"Bearer {acesso}"}).status_code == 401


def test_entrar_com_senha_pelo_app(cli):
    _cadastra(cli)
    cli.cookies.clear()
    errado = cli.post("/api/auth/entrar", json={"email": "ana@exemplo.com", "senha": "senha-errada-123"})
    inexistente = cli.post("/api/auth/entrar", json={"email": "ninguem@exemplo.com", "senha": SENHA})
    assert errado.status_code == inexistente.status_code == 401
    assert errado.json() == inexistente.json()  # mesma resposta: não diz se o e-mail existe
    r = cli.post("/api/auth/entrar", json={"email": "ana@exemplo.com", "senha": SENHA, "cliente": "app"})
    assert r.status_code == 200 and "pl_acesso" not in cli.cookies
    tok = r.json()
    assert tok["acesso"].startswith("pla_") and tok["renovacao"].startswith("plr_")
    h = {"Authorization": f"Bearer {tok['acesso']}"}
    assert cli.get("/api/perfil", headers=h).status_code == 200
    assert cli.post("/api/auth/sair", headers=h).status_code == 200  # cabeçalho não precisa de origem
    assert cli.get("/api/perfil", headers=h).status_code == 401


def test_renovacao_com_rotacao_e_deteccao_de_reuso(cli):
    tok = _cadastra(cli, cliente="app").json()
    r1 = cli.post("/api/auth/renovar", json={"renovacao": tok["renovacao"]})
    assert r1.status_code == 200 and r1.json()["renovacao"] != tok["renovacao"]
    novo = r1.json()
    assert cli.get("/api/perfil", headers={"Authorization": f"Bearer {tok['acesso']}"}).status_code == 401
    assert cli.get("/api/perfil", headers={"Authorization": f"Bearer {novo['acesso']}"}).status_code == 200
    # O token velho aparece de novo: alguém copiou. A família inteira cai, inclusive o par novo.
    assert cli.post("/api/auth/renovar", json={"renovacao": tok["renovacao"]}).status_code == 401
    assert cli.get("/api/perfil", headers={"Authorization": f"Bearer {novo['acesso']}"}).status_code == 401
    assert cli.post("/api/auth/renovar", json={"renovacao": novo["renovacao"]}).status_code == 401


def test_renovacao_pelo_cookie_do_painel(cli):
    _cadastra(cli)
    antigo = cli.cookies["pl_acesso"]
    assert cli.post("/api/auth/renovar").status_code == 403  # sem origem
    r = cli.post("/api/auth/renovar", headers=ORIGEM)
    assert r.status_code == 200 and cli.cookies["pl_acesso"] != antigo
    assert "renovacao" not in r.json()  # no painel, o token não aparece para o JavaScript


def test_trocar_senha_pede_a_atual_e_derruba_os_outros_aparelhos(cli):
    outro = _cadastra(cli, cliente="app").json()
    eu = cli.post("/api/auth/entrar", json={"email": "ana@exemplo.com", "senha": SENHA, "cliente": "app"}).json()
    h = {"Authorization": f"Bearer {eu['acesso']}"}
    nova = "trilha-da-serra-2026"
    assert (
        cli.post("/api/auth/trocar-senha", json={"atual": "errada-errada", "nova": nova}, headers=h).status_code == 403
    )
    assert cli.post("/api/auth/trocar-senha", json={"atual": SENHA, "nova": nova}, headers=h).status_code == 200
    assert cli.get("/api/perfil", headers=h).status_code == 200
    assert cli.get("/api/perfil", headers={"Authorization": f"Bearer {outro['acesso']}"}).status_code == 401
    assert cli.post("/api/auth/entrar", json={"email": "ana@exemplo.com", "senha": nova}).status_code == 200


def test_sair_de_todos(cli):
    a = _cadastra(cli, cliente="app").json()
    b = cli.post("/api/auth/entrar", json={"email": "ana@exemplo.com", "senha": SENHA, "cliente": "app"}).json()
    assert cli.post("/api/auth/sair-de-todos", headers={"Authorization": f"Bearer {a['acesso']}"}).status_code == 200
    for t in (a, b):
        assert cli.get("/api/perfil", headers={"Authorization": f"Bearer {t['acesso']}"}).status_code == 401


def test_limite_de_tentativas_erradas(cli):
    _cadastra(cli)
    for _ in range(MAX_POR_EMAIL_IP):
        assert (
            cli.post("/api/auth/entrar", json={"email": "ana@exemplo.com", "senha": "chute-errado-1"}).status_code
            == 401
        )
    r = cli.post("/api/auth/entrar", json={"email": "ana@exemplo.com", "senha": SENHA})
    assert r.status_code == 429 and "Retry-After" in r.headers
    # Outra conta no mesmo IP continua podendo entrar (o limite não trava todo mundo).
    _cadastra(cli, email="bia@exemplo.com")
    assert cli.post("/api/auth/entrar", json={"email": "bia@exemplo.com", "senha": SENHA}).status_code == 200


def test_token_antigo_continua_valendo_na_transicao(cli):
    assert cli.get("/api/perfil", headers={"Authorization": "Bearer teste"}).status_code == 200
    assert cli.get("/api/auth/eu", headers={"Authorization": "Bearer teste"}).status_code == 401
    assert cli.get("/api/perfil", headers={"Authorization": "Bearer chute"}).status_code == 401


def _google(cli, monkeypatch, dados):
    """Faz o vaivém do Google, com a troca do código simulada."""
    r = cli.get("/api/auth/google/iniciar", follow_redirects=False)
    assert r.status_code == 302
    url = urlparse(r.headers["location"])
    q = parse_qs(url.query)
    assert url.netloc == "accounts.google.com"
    assert q["code_challenge_method"] == ["S256"] and q["redirect_uri"] == [f"{URL}/api/auth/google/retorno"]
    assert {"state", "nonce", "code_challenge"} <= q.keys()
    vistos = {}

    def falsa_troca(settings, codigo, verificador, nonce):
        vistos.update(codigo=codigo, verificador=verificador, nonce=nonce)
        return dados

    monkeypatch.setattr(contas, "trocar_codigo_google", falsa_troca)
    state = q["state"][0]
    r = cli.get(f"/api/auth/google/retorno?state={state}&code=codigo-1", follow_redirects=False)
    assert vistos.get("nonce", q["nonce"][0]) == q["nonce"][0]
    return r, state


def test_login_com_google_cria_a_conta_convidada(cli, monkeypatch):
    dados = {"sub": "g-123", "email": "Bia@Exemplo.com", "email_verified": True, "name": "Bia"}
    r, state = _google(cli, monkeypatch, dados)
    assert r.status_code == 302 and r.headers["location"] == "/"
    eu = cli.get("/api/auth/eu").json()
    assert eu["email"] == "bia@exemplo.com" and eu["google"] and not eu["senha"]
    # O mesmo state não serve duas vezes.
    r2 = cli.get(f"/api/auth/google/retorno?state={state}&code=codigo-1", follow_redirects=False)
    assert "erro_login=google_falhou" in r2.headers["location"]


def test_login_com_google_sem_convite_ou_sem_email_confirmado(cli, monkeypatch):
    r, _ = _google(cli, monkeypatch, {"sub": "g-9", "email": "intrusa@exemplo.com", "email_verified": True})
    assert "erro_login=google_sem_convite" in r.headers["location"]
    r, _ = _google(cli, monkeypatch, {"sub": "g-8", "email": "ana@exemplo.com", "email_verified": False})
    assert "erro_login=google_sem_convite" in r.headers["location"]
    assert cli.get("/api/auth/eu").status_code == 401


def test_google_liga_na_conta_de_senha_existente(cli, monkeypatch):
    _cadastra(cli)
    cli.cookies.clear()
    _google(cli, monkeypatch, {"sub": "g-ana", "email": "ana@exemplo.com", "email_verified": True})
    eu = cli.get("/api/auth/eu").json()
    assert eu["email"] == "ana@exemplo.com" and eu["google"] and eu["senha"]


def test_google_recusa_retorno_de_outro_navegador(cli, monkeypatch):
    r = cli.get("/api/auth/google/iniciar", follow_redirects=False)
    state = parse_qs(urlparse(r.headers["location"]).query)["state"][0]
    monkeypatch.setattr(contas, "trocar_codigo_google", lambda *a: pytest.fail("não deveria chamar o Google"))
    cli.cookies.clear()  # outro navegador: sem o cookie de vínculo
    r = cli.get(f"/api/auth/google/retorno?state={state}&code=x", follow_redirects=False)
    assert "erro_login=google_falhou" in r.headers["location"]


def test_google_desligado_sem_configuracao(db, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    get_settings.cache_clear()
    with TestClient(app, base_url=URL) as c:
        assert c.get("/api/auth/google/iniciar", follow_redirects=False).status_code == 404
