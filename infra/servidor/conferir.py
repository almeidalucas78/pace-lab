"""Confere um Pace Lab no ar (fase 9, etapa 10): saúde, painel, rotas protegidas e, se pedido, o login.

Uso: python3 conferir.py http://127.0.0.1:8000
Com CONFERIR_EMAIL e CONFERIR_SENHA (só no CI, conta descartável na lista CADASTRO_EMAILS), também cria a conta,
entra por cookie como o navegador atrás do Tailscale (X-Forwarded-Proto: https) e renova a sessão. Isso prova que
as migrações rodaram no Postgres e que a API enxerga o HTTPS do proxy (sem isso o cookie seria recusado).
Só biblioteca padrão: roda no servidor sem instalar nada. Sai com código 1 na primeira falha.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ESPERA_S = 180  # primeira subida: o Postgres inicia e as migrações rodam


def pedir(
    url: str,
    metodo: str = "GET",
    corpo: dict | None = None,
    cabecalhos: dict | None = None,
):
    dados = json.dumps(corpo).encode() if corpo is not None else None
    req = urllib.request.Request(
        url, data=dados, method=metodo, headers=cabecalhos or {}
    )
    if dados is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.headers, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read()


def falha(msg: str) -> None:
    print(f"FALHOU: {msg}")
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"ok: {msg}")


def cookies(cabecalhos) -> dict[str, str]:
    """Nome e valor de cada Set-Cookie (o urllib não guarda cookie Secure em http)."""
    achados = {}
    for linha in cabecalhos.get_all("Set-Cookie") or []:
        nome, _, resto = linha.partition("=")
        achados[nome.strip()] = resto.split(";", 1)[0]
    return achados


def main(base: str) -> None:
    base = base.rstrip("/")
    fim = time.monotonic() + ESPERA_S
    while True:
        try:
            status, _, corpo = pedir(f"{base}/api/health")
            if status == 200 and json.loads(corpo).get("status") == "ok":
                break
        except (OSError, ValueError):
            pass
        if time.monotonic() > fim:
            falha(f"/api/health não respondeu em {ESPERA_S} s")
        time.sleep(3)
    ok("/api/health")

    status, _, corpo = pedir(f"{base}/")
    if status != 200 or b'id="root"' not in corpo:
        falha(f"painel em / (status {status})")
    ok("painel compilado servido em /")

    status, _, _ = pedir(f"{base}/api/overview")
    if status != 401:
        falha(f"/api/overview sem login deveria dar 401, deu {status}")
    ok("rotas de dados pedem login")

    email, senha = os.environ.get("CONFERIR_EMAIL"), os.environ.get("CONFERIR_SENHA")
    if not (email and senha):
        print("Tudo certo.")
        return

    status, _, corpo = pedir(
        f"{base}/api/auth/cadastro",
        "POST",
        {"email": email, "senha": senha, "cliente": "app"},
    )
    if status != 201:
        falha(f"cadastro deu {status}: {corpo[:200]!r}")
    acesso = json.loads(corpo)["acesso"]
    status, _, corpo = pedir(
        f"{base}/api/perfil", cabecalhos={"Authorization": f"Bearer {acesso}"}
    )
    if status != 200:
        falha(f"/api/perfil com token deu {status}")
    ok("conta criada e perfil lido (migrações aplicadas no banco)")

    # Navegador atrás do Tailscale: o proxy fala https com o celular e http com a API.
    host = urlsplit(base).netloc
    proxy = {"X-Forwarded-Proto": "https", "Origin": f"https://{host}"}
    status, cab, _ = pedir(
        f"{base}/api/auth/entrar", "POST", {"email": email, "senha": senha}, proxy
    )
    biscoitos = cookies(cab)
    if status != 200 or "pl_renovacao" not in biscoitos:
        falha(f"entrar pelo navegador deu {status}, cookies {sorted(biscoitos)}")
    status, _, corpo = pedir(
        f"{base}/api/auth/renovar",
        "POST",
        None,
        proxy | {"Cookie": f"pl_renovacao={biscoitos['pl_renovacao']}"},
    )
    if status != 200:
        falha(
            f"renovar com cookie atrás do proxy deu {status}: {corpo[:200]!r} (o X-Forwarded-Proto chegou?)"
        )
    ok("login por cookie e renovação atrás do proxy https")
    print("Tudo certo.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1])
