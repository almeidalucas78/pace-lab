# Contribuindo

Guia para montar o ambiente de desenvolvimento e rodar as checagens. O fluxo de trabalho (issues, branches, pull requests, fases) está em [docs/processo.md](docs/processo.md); as regras do projeto, em [AGENTS.md](AGENTS.md).

## Ambiente

Pré-requisitos: Python 3.11 ou mais novo, Node.js 18 ou mais novo, Git. No Windows, pelo PowerShell, na pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e "./server[dev]"
copy .env.example .env
cd web
npm install
```

O app Android (`android/`) precisa também do JDK 21, do Android SDK e do Samsung Health Data SDK, baixado à parte (não pode ser redistribuído, por isso não está no repositório); o passo a passo está em [docs/celular.md](docs/celular.md).

## Checagens antes de abrir um pull request

Uma vez, depois de montar o ambiente: `.\.venv\Scripts\pre-commit.exe install`. A partir daí, cada commit roda as checagens rápidas (ruff, checagens do projeto, oxlint) nos arquivos alterados.

Antes de abrir um pull request, rode tudo:

```powershell
.\.venv\Scripts\pre-commit.exe run --all-files    # ruff, checagens do projeto, oxlint
cd server; ..\.venv\Scripts\mypy.exe; cd ..          # tipos do Python
.\.venv\Scripts\python.exe -m pytest -q server       # testes do backend
cd web; npm run lint; npm run build; npm test         # painel: lint, tipos, build e testes
```

O CI do GitHub roda as mesmas checagens em todo pull request. Por que cada ferramenta: [ADR 0016](docs/decisions/0016-qualidade-de-codigo.md).

### Padrões privados
Para o `scripts/checagens.py` barrar também dados seus que não podem aparecer no repositório (nome da sua rede, do seu aparelho), escreva um por linha em `data/checagens-locais.txt`. A pasta `data/` nunca vai para o git.

## Regras que mais pegam

- Testes só com dados sintéticos gerados no próprio teste. Nada de arquivos reais de treino (têm GPS).
- Textos em português do Brasil, sem o caractere travessão (U+2014).
- Mudança no esquema do banco exige migração do Alembic e conversa antes (`.claude/rules/banco.md`).
- Commits no formato `tipo(área): descrição`, com o tipo em inglês: `feat(web): tela de login`.
