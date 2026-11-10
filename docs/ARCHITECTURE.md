# Arquitetura

Visão de como o sistema é montado hoje e como ele cresce. As decisões por trás de cada escolha estão em [decisions/](decisions/README.md).

## Camadas

```
            interfaces (só chamam services)
  ┌──────────┬──────────┬──────────┬──────────┬────────────┐
  │ CLI      │ API      │ agendador│ MCP      │ chat (IA)  │
  │ cli.py   │ api/     │scheduler │ ia/mcp_  │ ia/chat.py │
  │          │          │   .py    │ server.py│ provedores │
  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴─────┬──────┘
       └──────────┴──────────┼──────────┴───────────┘
                             ▼
                 services.py  (regras e consultas)
                 ▲           │            ▲
     ingest/ ────┘           ▼            └──── core/
  (adaptadores de fonte)   db/ (SQLAlchemy)   (cálculo puro)
```

| Pacote | Papel | Pode depender de |
|---|---|---|
| `core/` | Parciais, limpeza de FC, zonas, TRIMP, fitness/fadiga/forma, aderência ao plano | nada do projeto além de `ingest.files.Point` |
| `ingest/` | Ler fontes e gravar treinos: export do Strava, HC Webhook | `core`, `db` |
| `db/` | Modelos, sessão, `init_db()` com Alembic | `config` |
| `services.py` | Única camada de regras e consultas | `core`, `db`, `ingest` |
| `ia/` | Ferramentas da IA, servidor MCP, provedores, chat | `services` |
| `api/`, `cli.py`, `scheduler.py` | Interfaces | `services`, `ia` |

O painel web (`web/`, ADR 0011) é um app React separado que fala só com a API, por HTTP:

| Pasta | Papel |
|---|---|
| `web/src/api/` | `cliente.ts` (token no navegador, prefixo `/api`, 401 volta para a tela do token), `tipos.ts` (tipos das respostas, escritos à mão), `consultas.ts` (TanStack Query) |
| `web/src/paginas/` | Visão geral, Treinos, Treino, Plano, Token |
| `web/src/componentes/` | gráficos (Recharts), mapa (Leaflet + OpenStreetMap), semanas do plano, chat lateral |
| `web/src/contexto.tsx` | o que está aberto na tela; o chat manda como `contexto` para a IA |

Em uso normal, `treino servico` serve o build (`web/dist`) na raiz e a API em `/api` (documentação em `/api/docs`), no mesmo processo. No desenvolvimento, `npm run dev` (porta 5173) repassa `/api` para o backend.

**Celular (ADR 0012):** o `tailscale serve --bg 8000` repassa `https://<pc>.<rede>.ts.net` para o 127.0.0.1:8000, só dentro do tailnet. O painel é um app instalável (PWA, `vite-plugin-pwa`): o service worker guarda só as telas (nunca `/api` nem o mapa); os dados ficam no IndexedDB pelo cache persistente do TanStack Query (`web/src/api/persistencia.ts`, 30 dias, `VERSAO_DADOS` descarta o cache quando o formato das respostas muda). `web/src/api/cliente.ts` marca "PC fora do ar" quando a busca falha ou o Tailscale responde 502 sem o JSON do backend. As páginas carregam sob demanda (`React.lazy`): o arquivo inicial tem cerca de 300 kB.

## Fluxo dos dados

**Histórico (Strava):** `treino importar-strava export.zip` → `ingest/strava_export.py` lê o `activities.csv` (`strava_csv.py`) e cada arquivo (`files.py`: GPX, TCX, FIT, com ou sem .gz) → `streams_store.save_streams()` → `core/streams.process_points()` limpa e gera amostras e parciais → banco → `services.recompute()`.

**Treinos novos (Health Connect):** agendador ou `treino sincronizar` → `services.sync_health_connect()` → `ingest/hc_client.py` faz `GET /?start=&end=` no celular → `ingest/health_connect.py` converte (cálculo puro) → `ingest/hc_import.py` grava (idempotente pelo id do Health Connect) → `recompute()` → notificação dos treinos novos que não são duplicata.

**Recálculo (`services.recompute`)**, sempre depois de importar: marca duplicatas (Strava prevalece), resolve a FC máxima (configurada ou estimada), calcula zonas e TRIMP por treino e refaz a série diária de fitness, fadiga e forma.

**Planos e aderência (ADR 0010):** a IA mostra o plano, o usuário confirma e ela chama `salvar_plano` → `services.create_plan()` grava `training_plans` e `planned_sessions` (o ativo anterior vira `substituido`). Na consulta, `services.plan_adherence()` busca os treinos sem duplicata de um dia antes a um dia depois do plano e chama `core/aderencia.py`, que casa sessão e treino (mesmo esporte no mesmo dia, senão dia vizinho), compara com as metas e monta o resumo por semana. O casamento não é gravado: é refeito a cada consulta.

**Chat:** `POST /api/chat` (painel) ou `treino chat` → `ia/chat.conversar()` → provedor (Claude Agent SDK ou Gemini) → a IA chama ferramentas de `ia/ferramentas.py` → `services` → fichas resumidas voltam para a IA → resposta gravada em `chat_messages`. O `contexto` enviado pelo painel (ex.: "o usuário está vendo o treino #356") vai para a IA, mas não é gravado na conversa.

## Banco

| Tabela | O que guarda | Recalculável? |
|---|---|---|
| `activities` | Um treino por fonte (`source`, `source_id`), totais, métricas, duplicata | sim, reimportando |
| `samples` | Leituras ao longo do treino (1/s) | sim |
| `splits` | Parciais por km | sim |
| `daily_load` | Carga diária, fitness, fadiga, forma | sim, `treino recalcular` |
| `sync_state` | Última sincronização por fonte | não |
| `sensations` | Como o usuário se sentiu (via chat) | **não** |
| `conversations`, `chat_messages` | Histórico do chat | **não** |
| `training_plans`, `planned_sessions` | Planos e sessões com metas (o casamento com treinos é calculado) | **não** |

Tabelas marcadas "não" têm dados que nenhum export recupera: nunca apagar, e fazer backup antes de migração arriscada.

Datas sempre em UTC com fuso (`UTCDateTime`); o fuso local (`TIMEZONE`) só é usado para agrupar por dia e semana e para mostrar.

## Configuração

Tudo em `.env` (modelo em `.env.example`), lido por `config.Settings`. O `.env` e o SQLite relativo são resolvidos pela raiz do projeto (`config.ROOT`), então os comandos funcionam de qualquer pasta.

## Como escalar

| Hoje (PC) | Ao hospedar |
|---|---|
| SQLite em `data/` | Postgres, trocando `DATABASE_URL` (migrações do Alembic já servem) |
| PC puxa do celular (`hc_client`) | HC Webhook envia webhook para a API (endpoint novo em `api/`) |
| `treino servico` aberto à mão | Docker Compose; o agendador continua dentro do processo |
| MCP por stdio | MCP via HTTP com autenticação, como conector customizado no claude.ai |
| Claude com login da assinatura | Claude com chave de API |
| Celular via Tailscale | Domínio público com HTTPS |

Pontos de atenção quando o volume crescer:
- `recompute()` refaz tudo a cada importação; com muitos anos de dados, passar a recalcular a partir do dia mais antigo alterado.
- `services.py` deve virar pacote `services/` quando passar de umas 800 linhas.
