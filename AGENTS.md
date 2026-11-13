# AGENTS.md

Instruções para qualquer agente de IA (Claude Code, Gemini CLI, outros) e para pessoas que trabalham neste repositório. O `CLAUDE.md` e o `GEMINI.md` só importam este arquivo; as regras comuns ficam aqui.

## O projeto

Pace Lab: sistema pessoal para analisar corridas (depois musculação) e montar planos de treino conversando com uma IA. Painel web com gráficos e chat embutido, app Android que lê o Samsung Health. Os planos nascem da conversa, não de regras fixas: o Python calcula métricas, a IA interpreta e propõe.

## Como retomar o trabalho

1. `docs/ROADMAP.md`: qual fase está em andamento (🚧) ou planejada (📝).
2. `docs/fases/fase-N.md` dessa fase: etapas marcadas e o que falta.
3. Issues abertas da fase: `gh issue list --milestone "Fase N"` (a partir da fase 8, etapa 7).
4. `git log --oneline -10` e `git status`: o que foi feito por último e o que ficou sem commit.
5. O processo completo (issue, branch, pull request, fechamento de fase) está em `docs/processo.md`.

## Regras de trabalho (sempre)

- Textos para o usuário e textos exibidos no sistema em português do Brasil.
- Nunca use travessão (o caractere U+2014) em nenhum texto gerado: código, comentários, docs, mensagens, commits.
- Nunca afirme como uma ferramenta, API ou plugin funciona sem checar a documentação oficial ou a web. Se não conseguir verificar, diga.
- Testes só com dados sintéticos. Nunca colocar os arquivos reais do usuário (têm GPS de onde ele mora) no repositório, nos testes, em issues ou em pull requests.
- Antes de decisões caras de desfazer (mudar esquema do banco, trocar biblioteca, apagar dados, reescrever histórico), pergunte.
- Antes de dizer que algo está pronto, rode as checagens de `CONTRIBUTING.md` (pre-commit, mypy, pytest; e, se mexeu em `web/`, `npm run lint`, `npm run build` e `npm test`).
- Decisões com status "aceita" em `docs/decisions/` não são reabertas sem perguntar. Decisão nova vira ADR na hora.
- Commit, push, abrir ou fechar pull request só com o ok do usuário.
- Mensagens de commit no formato Conventional Commits, com o tipo em inglês e o texto em português: `feat(web): tela de login`, `fix(ingest): parciais do Samsung`, `docs: plano da fase 9`. Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`, `build`.

## Nunca vai para o repositório

`.env`, `data/`, `*.db`, arquivos de treino (`*.gpx`, `*.tcx`, `*.fit`, `*.json.gz`, `activities*`), `*.zip`, o SDK da Samsung (`*.aar`, `samsung-health-data-sdk*`), APKs, chaves e tokens (`AIza...`, `sk-ant...`, o valor do `API_TOKEN`), o endereço real do Tailscale do usuário e o nome do aparelho dele. Ao inspecionar dados reais, use scripts fora do repositório que não imprimem coordenadas.

## Regras por área

Antes de mexer numa área, leia a regra dela (o Claude Code carrega sozinho; outras IAs devem abrir o arquivo):

| Área | Regra |
|---|---|
| Banco e migrações (`server/treino/db/`, `server/treino/migrations/`) | `.claude/rules/banco.md` |
| IA, ferramentas e MCP (`server/treino/ia/`) | `.claude/rules/ia.md` |
| Leitores, cálculos e testes (`server/treino/ingest/`, `server/treino/core/`, `server/tests/`) | `.claude/rules/ingest-e-testes.md` |
| Painel web (`web/`) | `.claude/rules/web.md` |

## Onde está cada coisa

| Preciso de... | Arquivo |
|---|---|
| Fases, status e pendências | `docs/ROADMAP.md` |
| Plano da fase atual | `docs/fases/fase-N.md` |
| Fluxo de trabalho (issues, PRs, fases) | `docs/processo.md` |
| Montar o ambiente e rodar as checagens | `CONTRIBUTING.md` |
| Por que algo é como é | `docs/decisions/` (índice no `README.md` de lá) |
| Camadas, fluxos, tabelas, como escalar | `docs/ARCHITECTURE.md` |
| Fatos sobre os dados reais do usuário | `docs/dados.md` |
| O que mudou em cada versão | `CHANGELOG.md` |
| Uso para o usuário (instalar, comandos, MCP) | `README.md` (celular: `docs/celular.md`) |
| Segurança | `SECURITY.md` |

## Mapa do código

```
server/          backend Python (pyproject.toml, alembic.ini)
  treino/
    config.py      .env, data/ e web/dist resolvidos pela raiz do repositório (config.ROOT)
    core/          cálculo puro: parciais, limpeza de FC, zonas, TRIMP, fitness/fadiga/forma, aderência ao plano
    ingest/        export do Strava, treinos do app Android (treinos_app: conversor e gravação), streams_store
    db/            modelos SQLAlchemy, sessão, init_db() com Alembic
    migrations/    versões do Alembic
    services.py    única camada de regras e consultas
    ia/            ferramentas (registro único), MCP, provedores Claude e Gemini, chat
    api/           FastAPI com token: rotas em /api, painel compilado (web/dist) na raiz
    notify.py      notificação do Windows
    cli.py         comandos `treino ...`
  tests/         pytest com dados sintéticos
web/             painel React + TypeScript + Vite (só fala com a API); capacitor.config.ts
android/         app Android (Capacitor) com o plugin do Samsung Health
scripts/         iniciar-treino.bat (sobe o serviço e abre o painel)
data/            banco, APK publicado e sessões do chat (fora do git)
```

## Ambiente do usuário

- Windows, Python 3.13 no `.venv`. O PC fica desligado da meia-noite às 8h.
- Galaxy Watch 7, Samsung Health, Health Connect no celular Android.
- Assinaturas: Claude (Claude Code), Gemini Pro (sem cota de API), Strava. Musculação no Hevy, que envia para o Strava.
- Custo zero: nada pago além de, no futuro, talvez a hospedagem.
- Export do Strava em `D:\dados\strava\export_<número>.zip` (o único `.zip` de export na pasta); backups do banco na mesma pasta.

## Comandos

```powershell
.\.venv\Scripts\pre-commit.exe run --all-files   # ruff, checagens do projeto, oxlint
cd server; ..\.venv\Scripts\mypy.exe; cd ..         # tipos (rigoroso em core/)
.\.venv\Scripts\python.exe -m pytest -q server
.\.venv\Scripts\treino.exe resumo
.\.venv\Scripts\treino.exe importar-strava "D:\dados\strava\export_<número>.zip"
.\.venv\Scripts\treino.exe servico      # painel + API para o app (scripts/iniciar-treino.bat)
.\.venv\Scripts\treino.exe publicar-app   # publica o APK compilado para o app se atualizar
.\.venv\Scripts\treino.exe chat         # --provedor gemini, --conversa N
.\.venv\Scripts\treino.exe mcp          # --http para 127.0.0.1:8001/mcp
cd web; npm run lint; npm run build; npm test   # painel (desenvolvimento: npm run dev, em :5173)
```
