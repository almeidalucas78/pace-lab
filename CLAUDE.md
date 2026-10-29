# CLAUDE.md

Projeto Treino (repositório pace-lab): sistema pessoal para analisar corridas (depois musculação) e montar planos de treino conversando com uma IA. Painel web com gráficos e chat embutido. Os planos nascem da conversa, não de regras fixas: o Python calcula métricas, a IA interpreta e propõe.

## Regras de trabalho (sempre)

- Textos para o usuário e textos exibidos no sistema em português do Brasil.
- Nunca use travessão (o caractere U+2014) em nenhum texto gerado: código, comentários, docs, mensagens, commits.
- Nunca afirme como uma ferramenta, API ou plugin funciona sem checar a documentação oficial ou a web. Se não conseguir verificar, diga.
- Testes só com dados sintéticos. Nunca colocar os arquivos reais do usuário (têm GPS de onde ele mora) no repositório ou nos testes.
- Antes de decisões caras de desfazer (mudar esquema do banco, trocar biblioteca, apagar dados), pergunte.
- Rode os testes (`pytest`) antes de dizer que algo está pronto.
- Decisões com status "aceita" em `docs/decisions/` não são reabertas sem perguntar. Decisão nova vira ADR na hora.
- Commit e push só com o ok do usuário.

## Onde está cada coisa

| Preciso de... | Arquivo |
|---|---|
| Fases, status e pendências | `docs/ROADMAP.md` |
| Plano da fase atual | `docs/fases/fase-N.md` |
| Por que algo é como é | `docs/decisions/` (índice no `README.md` de lá) |
| Camadas, fluxos, tabelas, como escalar | `docs/ARCHITECTURE.md` |
| Fatos sobre os dados reais do usuário | `docs/dados.md` |
| O que mudou em cada versão | `CHANGELOG.md` |
| Uso para o usuário (instalar, comandos, MCP) | `README.md` |
| Regras por pasta (banco, ingest, IA) | `.claude/rules/` (carregam sozinhas) |

## Fluxo de cada fase

1. `/planejar-fase N`: lê o estado, escreve `docs/fases/fase-N.md`, apresenta e **espera o ok**.
2. Implementação etapa por etapa, marcando o plano; decisões viram ADR.
3. `/fechar-fase N`: testes, critério de pronto, docs, checagem de dados pessoais, commit com ok.

## Mapa do código

```
treino/
  config.py      .env (resolvido pela raiz do projeto, config.ROOT)
  core/          cálculo puro: parciais, limpeza de FC, zonas, TRIMP, fitness/fadiga/forma, aderência ao plano
  ingest/        export do Strava, HC Webhook (cliente, conversor, gravação), streams_store
  db/            modelos SQLAlchemy, sessão, init_db() com Alembic
  migrations/    versões do Alembic
  services.py    única camada de regras e consultas
  ia/            ferramentas (registro único), MCP, provedores Claude e Gemini, chat
  api/           FastAPI com token
  scheduler.py   sincronização periódica dentro do serviço
  notify.py      notificação do Windows
  cli.py         comandos `treino ...`
tests/           pytest com dados sintéticos
```

## Ambiente do usuário

- Windows, Python 3.13 no `.venv`. O PC fica desligado da meia-noite às 8h.
- Galaxy Watch 7, Samsung Health, Health Connect no celular Android.
- Assinaturas: Claude (Claude Code), Gemini Pro (sem cota de API), Strava. Musculação no Hevy, que envia para o Strava.
- Sem gastar com hospedagem por enquanto; a arquitetura deve estar pronta para hospedar.
- Export do Strava em `D:\dados\strava\export_<número>.zip`; backups do banco na mesma pasta.

## Comandos

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\treino.exe resumo
.\.venv\Scripts\treino.exe importar-strava "D:\dados\strava\export_<número>.zip"
.\.venv\Scripts\treino.exe servico      # API + sincronização (iniciar-treino.bat)
.\.venv\Scripts\treino.exe sincronizar
.\.venv\Scripts\treino.exe chat         # --provedor gemini, --conversa N
.\.venv\Scripts\treino.exe mcp          # --http para 127.0.0.1:8001/mcp
```
