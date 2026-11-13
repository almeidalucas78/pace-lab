"""Checagens do projeto que nenhuma ferramenta pronta faz: regras do AGENTS.md sobre textos e dados pessoais.

Uso:
    python scripts/checagens.py            # todos os arquivos versionados
    python scripts/checagens.py ARQ ...    # só os arquivos dados (o pre-commit passa os alterados)

Padrões extras e privados (ex.: o nome real da rede do Tailscale ou do celular) podem ficar em
`data/checagens-locais.txt`, um por linha; a pasta `data/` nunca vai para o repositório.
Sai com código 1 se encontrar problema.
"""

from __future__ import annotations

import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TRAVESSAO = "—"

# Arquivos que nunca podem ser versionados (dados pessoais, segredos, binários de terceiros)
PROIBIDOS = [
    ".env",
    "*.db",
    "*.db-wal",
    "*.db-shm",
    "*.sqlite",
    "*.gpx",
    "*.gpx.gz",
    "*.tcx",
    "*.tcx.gz",
    "*.fit",
    "*.fit.gz",
    "*.json.gz",
    "*.zip",
    "*.aar",
    "*.apk",
    "data/*",
    "activities*",
    "*samsung-health-data-sdk*",
]

# Segredos conhecidos (o gitleaks no CI cobre o resto)
SEGREDOS = [
    ("chave do Google (Gemini)", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("chave da Anthropic", re.compile(r"sk-ant-[0-9A-Za-z_\-]{20,}")),
    ("chave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]

# Arquivos que citam os padrões de propósito (documentação das próprias regras)
IGNORAR_CONTEUDO = {"scripts/checagens.py"}


def arquivos_versionados() -> list[str]:
    saida = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout
    return [linha for linha in saida.splitlines() if linha]


def padroes_locais() -> list[str]:
    arq = RAIZ / "data" / "checagens-locais.txt"
    if not arq.exists():
        return []
    linhas = arq.read_text(encoding="utf-8").splitlines()
    return [p.strip() for p in linhas if p.strip() and not p.startswith("#")]


def checar(caminhos: list[str]) -> list[str]:
    problemas: list[str] = []
    locais = padroes_locais()
    for rel in caminhos:
        rel = rel.replace("\\", "/")
        nome = rel.rsplit("/", 1)[-1]
        if any(fnmatch(rel, p) or fnmatch(nome, p) for p in PROIBIDOS) and not rel.endswith(".env.example"):
            problemas.append(f"{rel}: arquivo proibido no repositório")
            continue
        if rel in IGNORAR_CONTEUDO:
            continue
        caminho = RAIZ / rel
        if not caminho.is_file():
            continue
        try:
            texto = caminho.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binário (imagens, jar)
        for n, linha in enumerate(texto.splitlines(), 1):
            if TRAVESSAO in linha:
                problemas.append(f"{rel}:{n}: travessão (U+2014); use vírgula, dois-pontos ou parênteses")
            for nome_seg, regex in SEGREDOS:
                if regex.search(linha):
                    problemas.append(f"{rel}:{n}: possível {nome_seg}")
            for p in locais:
                if p.lower() in linha.lower():
                    problemas.append(f"{rel}:{n}: padrão privado de data/checagens-locais.txt")
    return problemas


def main(argv: list[str]) -> int:
    caminhos = argv or arquivos_versionados()
    problemas = checar(caminhos)
    for p in problemas:
        print(p)
    if problemas:
        print(f"\n{len(problemas)} problema(s) encontrado(s).")
        return 1
    print(f"Checagens ok ({len(caminhos)} arquivos).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
