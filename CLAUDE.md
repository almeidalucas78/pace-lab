# CLAUDE.md

Contexto e regras do projeto Treino. Leia antes de qualquer alteração.

## Regras de trabalho (sempre)

- Textos para o usuário e textos exibidos no sistema em português do Brasil.
- Nunca use travessão (o caractere U+2014) em nenhum texto gerado: código, comentários, docs, mensagens, commits.
- Nunca afirme como uma ferramenta, API ou plugin funciona sem checar a documentação oficial ou a web. Se não conseguir verificar, diga.
- Testes só com dados sintéticos. Nunca colocar os arquivos reais do usuário (têm GPS de onde ele mora) no repositório ou nos testes.
- Antes de decisões caras de desfazer (mudar esquema do banco, trocar biblioteca, apagar dados), pergunte.
- Rode os testes (`pytest`) antes de dizer que algo está pronto.
- As decisões da seção "Decisões tomadas" não devem ser reabertas sem perguntar.

## Objetivo

Sistema pessoal para analisar corridas (depois musculação) e montar planos de treino conversando com uma IA. Painel web com gráficos e chat embutido. Os planos nascem da conversa no chat, não de regras fixas no código: o Python calcula métricas, a IA interpreta e propõe.

## Ambiente do usuário

- Windows, Python. O PC fica desligado da meia-noite às 8h.
- Galaxy Watch 7, Samsung Health, Health Connect no celular Android.
- Assinaturas: Claude (Claude Code), Gemini Pro (Google AI Pro), Strava.
- Musculação registrada no Hevy, que envia para o Strava.
- Sem gastar com hospedagem por enquanto, mas a arquitetura deve estar pronta para hospedar depois.

## Decisões tomadas

### Fontes de dados
- **Nunca usar a API do Strava.** A política da API (junho/2026) proíbe usar dados da API em qualquer aplicação de IA, incluindo prompt ou contexto, e limita cache a 7 dias. O Strava entra só pelo export completo da conta (importação única do histórico, já implementada). O conector MCP oficial do Strava pode ser usado no Claude separadamente, mas os dados dele não entram no nosso banco.
  - Conferido no texto oficial (strava.com/legal/api_policy, vigente desde 1/6/2026), em 27/10/2026: a seção 5.3 proíbe usar dados da API, ou dados derivados deles, para "operate an AI Application", incluindo "ingestion into a context window or working memory"; a única exceção é o Strava MCP (seção 3.5, uso pessoal de assinantes). A seção 6.2 limita cache a 7 dias e a 5.5 proíbe índice persistente. Não há exceção para uso pessoal ou app de um usuário só. A seção 6.6 garante o direito de exportar os próprios dados (o caminho usado aqui).
  - Em 27/10/2026 o usuário pediu para reavaliar o uso da API caso a limitação do Health Connect (sem GPS) se confirme. Em 28/10/2026 ele disse que quer testar depois, junto com o Health Connect. Decisão pendente; até lá, nada de API.
- **Treinos novos vêm do Health Connect** pelo app HC Webhook (Play Store), com o servidor HTTP local ativado no celular (porta padrão 8787, token Bearer opcional que vamos ativar). O PC PUXA os dados pela Wi-Fi com `GET /?start=...&end=...`, pedindo sempre tudo desde a última importação.
- Não usar o modo webhook enquanto o sistema roda no PC: se o PC estiver desligado, o envio falha e o app só olha 48h para trás.
- **Deduplicação entre fontes:** histórico do Strava, treinos novos do Health Connect. Casar pelo horário de início e esporte. Quando o mesmo treino existir nas duas fontes, o Strava prevalece (o do Health Connect fica marcado como duplicata).
- **Início do serviço no PC:** o usuário roda manualmente um executável/atalho ao ligar o PC (sem início automático por enquanto; ele pode criar isso depois). O agendador interno roda enquanto o serviço estiver aberto e, ao iniciar, recupera o que ficou para trás.

### Stack
- Backend Python: FastAPI, SQLAlchemy, SQLite agora e Postgres depois trocando só `DATABASE_URL`.
- Migrações com Alembic (adotado na fase 2). `init_db()` aplica as migrações sozinho e reconhece banco da fase 1 (sem `alembic_version`) marcando-o como `0001`. No SQLite as migrações rodam com `foreign_keys=OFF`, porque o batch do Alembic recria tabelas e, com FK ligada, apagaria amostras em cascata. Toda mudança de modelo precisa de migração nova (`alembic revision --autogenerate -m "..."`), revisada à mão.
- Notificações do Windows com `winotify` (usa o PowerShell, sem dependências); em outro sistema, só log.
- IA: `mcp` 2.x (API v2: `MCPServer`, não `FastMCP`), `claude-agent-sdk` (traz o `claude.exe` embutido), `google-genai` 2.x (`generate_content` com laço manual de ferramentas). APIs conferidas no pacote instalado em 28/10/2026.
- Front: React + TypeScript + Vite, responsivo, virando PWA na fase mobile. Nada de Streamlit.

### Arquitetura em camadas
- `core/`: só cálculo puro (sem banco, sem IO).
- `ingest/`: leitura de fontes, como adaptadores.
- `services.py`: única camada de regras e consultas.
- CLI, API e MCP chamam só `services.py`. Toda interface fala com a API, nunca direto com o banco.
- O agendamento roda dentro do próprio serviço (não no Agendador do Windows), para funcionar igual num servidor.

### Hospedagem futura
- Docker Compose, Postgres, HC Webhook enviando webhook direto para a API.
- MCP via HTTP adicionado como conector customizado no claude.ai (o Claude no celular só acessa MCP remoto público).
- Antes de hospedar, acesso pelo celular via Tailscale (plano pessoal gratuito), com o PC ligado.

### Chat e IA
- Chat dentro do painel: o backend chama a IA e expõe para ela as mesmas ferramentas do MCP (ex.: `ultimo_treino`, `detalhe_treino`, `resumo_semana`, `carga_atual`, `salvar_plano`, `registrar_sensacao`).
- As ferramentas devolvem fichas resumidas, não dados brutos, para economizar token.
- Provedores intercambiáveis por configuração:
  - Claude via Claude Agent SDK com o login da assinatura (uso pessoal no PC; consome os limites da assinatura). Ao hospedar, trocar para chave de API.
    - Atenção (docs oficiais do Agent SDK, conferidas em 28/10/2026): a documentação só descreve autenticação por chave de API e diz que, salvo aprovação, "third party developers" não podem oferecer login do claude.ai ou limites de assinatura em produtos feitos com o SDK. O uso aqui é do próprio assinante no próprio PC, não um produto oferecido a terceiros, mas a documentação não trata esse caso explicitamente. Usuário informado; nunca expor o chat com login de assinatura para outras pessoas.
  - Gemini via chave gratuita do Google AI Studio. Limites aparecem no painel do AI Studio; requisições do plano gratuito podem ser usadas pelo Google para melhorar produtos. A assinatura Gemini Pro não dá cota de API.
- Também usar via MCP local no Claude Desktop/Code e no Antigravity CLI (`agy`, que substituiu o Gemini CLI; MCP configurado em `~/.gemini/config/mcp_config.json`).

## Estado atual (fase 3 concluída; fase 2 falta validar com o celular)

### Fase 3
- `ia/ferramentas.py`: registro único das ferramentas (`ultimo_treino`, `detalhe_treino`, `listar_treinos`, `resumo_semanas`, `carga_atual`, `perfil_atleta`, `registrar_sensacao`, `ver_sensacoes`, `status_sincronizacao`). Esquema JSON gerado das anotações de tipo; `executar()` valida e devolve `{"erro": ...}` em vez de exceção. Fichas sem amostras brutas nem GPS.
- `ia/mcp_server.py`: `treino mcp` (stdio) e `treino mcp --http` (127.0.0.1:8001/mcp, sem autenticação). Testado com cliente MCP real aberto a partir de `C:\`.
- `ia/provedores.py`: `Claude` (Agent SDK, ferramentas num servidor MCP dentro do processo, `tools=[]` sem acesso a arquivos/comandos, `setting_sources=[]`, `permission_mode="dontAsk"`, sessão retomada por `resume`, cwd `data/chat-claude`) e `Gemini` (histórico vindo do banco, devolve o conteúdo do modelo inteiro para manter as assinaturas de raciocínio).
- `ia/prompt.py`: instruções fixas (sem data, para cache); a data vai no começo de cada mensagem.
- `ia/chat.py`: `conversar()` grava pergunta e resposta em `conversations`/`chat_messages`; conversa fica presa ao provedor em que começou.
- API: `POST /chat`, `GET /chat/conversas`, `GET /chat/conversas/{id}`, `GET /sensacoes`. CLI: `treino chat`, `treino mcp`. Tabelas novas (migração 0003): `sensations`, `conversations`, `chat_messages`.
- `.env` e SQLite relativo agora são resolvidos pela raiz do projeto (`config.ROOT`), de qualquer pasta.
- Teste real com Claude em 28/10/2026: funcionou com o login do Claude Code do PC (sem `ANTHROPIC_API_KEY`), cerca de 12 s por resposta, e a continuação pela API retomou a sessão. Gemini só testado com cliente falso (falta a chave).
- 22 testes passando.

### Fase 2
- `ingest/hc_client.py`: cliente do servidor local do HC Webhook (`GET /ping`, `GET /?start=&end=`, token Bearer).
- `ingest/health_connect.py`: conversão pura do JSON, escrita a partir da documentação do app, ainda sem JSON real. Recorta FC por sessão; aceita FC em amostras ou agregada; distância por ponto só com registros de até 2 min (senão não inventa parciais); trata `deleted`.
- `ingest/hc_import.py`: grava com `source="health_connect"` e `source_id` = `metadata.id` do Health Connect (idempotente).
- `services.sync_health_connect()`: lê desde o último sucesso menos `SYNC_MARGEM_H` (48 h), ou os últimos 30 dias na primeira vez; se o celular não responder, guarda o erro e não avança a janela. Tabela `sync_state`.
- Duplicatas com prioridade por fonte (`SOURCE_PRIORITY`: Strava vence).
- `scheduler.py`: thread dentro do serviço, roda ao iniciar e a cada `SYNC_INTERVALO_MIN`; notifica treinos novos que não são duplicata.
- CLI: `treino servico`, `treino sincronizar`, `treino status-sync`. API: `GET /sync/status`, `POST /sync`. `iniciar-treino.bat` na raiz.
- 16 testes passando. Teste de ponta a ponta feito com um servidor falso imitando o app.

### Fase 1
- Importador do export do Strava (pasta ou .zip), idempotente. Lê GPX, TCX e FIT, com e sem .gz, e guarda JSON de musculação em `extra`.
- Métricas: parciais por km, limpeza conservadora de FC, alerta de FC colada na cadência, zonas por % da FC máxima, carga TRIMP de Edwards, fitness (42 dias), fadiga (7 dias) e forma. Duplicatas marcadas.
- CLI `treino` e API FastAPI com token.
- Validado com o `activities.csv` real (359 atividades) e 9 arquivos de exemplo.

## Fatos sobre os dados do usuário

- `activities.csv` com datas em português e em UTC; colunas com nome repetido (o segundo bloco é numérico: distância em metros). O ID da atividade no CSV é diferente do número no nome do arquivo.
- Cadência de corrida exportada por perna (multiplicar por 2); a de caminhada já vem total.
- Corridas recentes em TCX (Samsung grava várias linhas com o mesmo horário: uma com FC, outra com cadência e velocidade). GPX do Samsung Health não traz o tipo de atividade.
- Musculação: 168 atividades; colunas de séries, repetições e peso total vazias no CSV; 59 têm arquivo .json.gz do Hevy (o 60º .json do zip é o `messaging.json`, que não é treino), 2 têm FIT e 107 não têm arquivo.
- FC sobe de forma contínua até 200 a 210 bpm em algumas corridas. `FC_MAX` não está configurada e a estimativa automática deu 214. Não trate isso como erro sem evidência; deixe claro que é estimativa. A estimativa não vem de um treino isolado: 10 corridas diferentes (2024 a 2025) têm pico sustentado de 30 s entre 207 e 214, coerente com a FC máxima do resumo do Strava.
- Export completo fica em `D:\dados\strava\export_<número>.zip` (fora do repositório).

## Pendências de validação

- [x] TCX recente `activities/21821148731.tcx.gz` (Watch 7, out/2026): uma linha por segundo, sem horários repetidos (o caso de linhas repetidas era de arquivos mais antigos). Traz FC, cadência por perna, velocidade, distância, GPS, altitude e `Watts` (potência de corrida, ainda não lida). `AverageHeartRateBpm` da volta vem vazio. Leitor funciona.
- [ ] Musculação (`activities/21901886126.json.gz` e os outros 58): todos do Hevy, mesmo formato. Raiz: `start_time`, `utc_offset`, `elapsed_time`, `active_time`, `total_calories`, `streams` (`time` em segundos relativos e `heartrate`) e `sets` (`exercise_type` em códigos tipo `SMITH_MACHINE_SQUAT`, `repetitions`, `weight` inteiro e, às vezes, `start_time` e `duration`). Unidade do peso não confirmada (provável kg). Decidir como guardar (fase 7).
- [x] Leitor de FIT testado com os 8 FIT reais (fev/2025): 2 corridas, 3 "training" e 3 "cycling" curtos (cerca de 3 min, sem distância). Todos leram sem erro.
- [ ] Ver um JSON real do HC Webhook (`GET /?days=2` depois de uma corrida) e ajustar `ingest/health_connect.py` ao formato real: valores de `type`, se `metadata` vem na sessão, resolução da FC, granularidade da distância, se existe rota/GPS. O usuário deixou a parte do celular para depois.
- [ ] Documentação do app se contradiz sobre token no servidor local (`local-http.md` tem Bearer; `usage.md` diz que não tem autenticação). Conferir no app.
- [x] Notificação do Windows (winotify) apareceu no teste de 27/10/2026.
- [ ] Testar o Gemini de verdade quando o usuário criar a `GEMINI_API_KEY` (modelo padrão `gemini-3.8-flash`, o "Stable" mais novo na página de modelos em 22/10/2026).
- [ ] Conferir no agy se o arquivo de MCP é `~/.gemini/config/mcp_config.json` (fontes divergem: alguns guias citam `~/.gemini/antigravity-cli/mcp_config.json`).

## Fases

1. Concluída.
2. Implementada; falta validar com o celular. Puxar treinos do celular (HC Webhook) + agendador no serviço + deduplicação com o histórico do Strava. Ao detectar treino novo, importar, analisar e mostrar notificação do Windows.
3. Concluída (backend e CLI; a interface do chat entra no painel na fase 5). Servidor MCP + chat com provedores Claude e Gemini.
4. Planos de treino (salvos pelo chat) e aderência planejado x executado.
5. Painel web desktop (React).
6. Painel no celular (responsivo + PWA, acesso via Tailscale).
7. Hospedagem e musculação (Hevy).

## Comandos úteis

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
treino importar-strava "caminho\do\export.zip"
treino resumo
treino servico      # ou dois cliques em iniciar-treino.bat
treino sincronizar
treino chat         # --provedor gemini, --conversa N
treino mcp          # --http para servir em 127.0.0.1:8001/mcp
```

O `.env` e o SQLite relativo são resolvidos pela raiz do projeto (`config.ROOT`), então os comandos funcionam de qualquer pasta.
