# Changelog

O que mudou em cada fase, escrito para o usuário. Formato inspirado no [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Detalhes técnicos ficam no git log.

## [Não lançado]

### Mudado
- Pastas reorganizadas: backend em `server/` (instalar com `pip install -e "./server[dev]"`, testes com `pytest -q server`), app Android em `android/`, `iniciar-treino.bat` em `scripts/`.
- Regras do projeto em `AGENTS.md`, lidas pelo Claude Code e pelo Gemini CLI; fluxo de trabalho em `docs/processo.md`; `CONTRIBUTING.md` e `SECURITY.md`.
- Repositório público, sem licença aberta (todos os direitos reservados).
- CI no GitHub Actions em todo pull request e na `main`: Python (ruff, mypy, pytest, pip-audit), painel (oxlint, tipos, build, testes, npm audit), regras do projeto e gitleaks em todo o histórico.
- Checagens de qualidade: ruff e mypy no Python, oxlint no painel, `scripts/checagens.py` (travessão, arquivos proibidos, segredos) e pre-commit antes de cada commit.

### Corrigido
- Pequenos ajustes apontados pelas checagens (tipos, data de "hoje" na visão geral calculada uma vez, erros encadeados com a causa).

## [0.7.0] - 2026-11-11 (fase 7)

### Adicionado
- App Android Pace Lab: lê os treinos do Samsung Health com GPS e os envia ao PC ao abrir, ao voltar e no botão Sincronizar.
- Esteira e musculação entram sem mapa; a distância sai da velocidade do relógio. Comando `treino reprocessar-app`.
- Atualização do app sem cabo: `treino publicar-app` no PC e o botão Atualizar no celular.
- Página Conectar celular com QR que abre o app já conectado.

### Corrigido
- Parciais dos treinos vindos do relógio: ritmos impossíveis (1:16/km) e FC faltando por km, porque GPS e sensores chegam com horários desencontrados. Treinos já recebidos corrigidos com `treino reprocessar-app`.

### Removido
- Sincronização por HC Webhook (cliente, agendador, `treino sincronizar`, `HC_URL`, `HC_TOKEN`, `SYNC_*` do `.env`). O celular passa a enviar os treinos.

## [0.6.0] - 2026-11-10 (fase 6)

### Adicionado
- Painel no celular pelo Tailscale, instalável como app (guia em `docs/celular.md`).
- Página **Conectar celular** com QR code: o celular abre já conectado, sem digitar o token.
- No celular: barra de navegação embaixo, chat em tela cheia, treinos em cartões, plano dia a dia, botão Atualizar.
- Dados já vistos ficam guardados no aparelho por até 30 dias; com o PC desligado o app mostra o que tinha, com o aviso "PC fora do ar" e a hora dos dados. Sair apaga tudo.
- Aviso de versão nova do painel.
- `PAINEL_URL_CELULAR` no `.env`; `treino servico` mostra o endereço do celular.

### Alterado
- O painel busca dados novos ao voltar para a janela ou o app.
- Páginas carregam sob demanda: o arquivo inicial caiu de cerca de 1 MB para 300 kB.
- Se algo quebrar ao desenhar uma tela, o painel mostra o erro e um botão para recarregar, em vez de ficar preto.

### Corrigido
- Chat derrubava o painel ao enviar uma mensagem no Chrome.
- Chat ficava vazio por um instante depois da resposta.
- Dados guardados no celular não apareciam com o PC fora do ar.

## [0.5.0] - 2026-11-02 (fase 5)

### Adicionado
- Painel web em http://127.0.0.1:8000 (o `iniciar-treino.bat` abre sozinho): visão geral com fitness, fadiga, forma, gráfico de 90 dias, volume semanal, última corrida e semana do plano; lista de treinos; cada treino com mapa, gráficos de FC, ritmo e altitude, parciais, zonas e sensações; plano por semanas com a situação de cada sessão e histórico.
- Chat com o treinador ao lado de qualquer página, com Claude ou Gemini, histórico de conversas e o contexto da página (a IA sabe qual treino ou plano está aberto).
- Rotas `/api/perfil` e `/api/carga/atual`; o detalhe do treino traz as sensações.
- `treino servico` avisa quem está ocupando a porta, em vez do erro técnico.

### Alterado
- A API passou para `/api/...` (documentação em `/api/docs`); a raiz agora é o painel.

### Corrigido
- Gemini: a chamada agora tem tempo limite (antes podia ficar presa vários minutos) e, quando o modelo principal está sobrecarregado (erro 503/504 do Google), a resposta usa o modelo de reserva (`GEMINI_MODELO_RESERVA`). A troca só acontece se nenhuma ferramenta já rodou, para não gravar nada duas vezes.

## [0.4.0] - 2026-10-28 (fase 4)

### Adicionado
- Planos de treino montados no chat: o treinador mostra, você confirma e ele salva. Ajustes pontuais e planos novos que substituem o anterior.
- Aderência ao plano: sessão feita, feita em dia vizinho, perdida, futura ou cancelada, comparada com distância, duração, ritmo e zona de FC; treinos extras; resumo por semana.
- Comando `treino plano` e rotas `/planos` na API.
- 7 ferramentas novas para a IA (também no MCP): `salvar_plano`, `plano_atual`, `aderencia_plano`, `alterar_sessao`, `adicionar_sessao`, `arquivar_plano`, `listar_planos`.
- Documentação do projeto: `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/dados.md` e decisões em `docs/decisions/`.
- Skills `/planejar-fase` e `/fechar-fase` para o ritual de cada fase.
- Regras do Claude Code por pasta em `.claude/rules/`.

## [0.3.0] - 2026-10-28 (fase 3)

### Adicionado
- Chat com o treinador: `treino chat` e `POST /chat`, com Claude (login do Claude Code do PC) ou Gemini (chave do AI Studio).
- Servidor MCP (`treino mcp`) com as mesmas 9 ferramentas do chat, para Claude Desktop, Claude Code e agy.
- Registro de sensações pelo chat (cansaço, dor, esforço percebido).
- Conversas salvas no banco e retomadas pelo id.

### Alterado
- `.env` e banco são encontrados pela pasta do projeto, de qualquer lugar.

## [0.2.0] - 2026-10-27 (fase 2)

### Adicionado
- Sincronização com o celular pelo HC Webhook: `treino servico`, `treino sincronizar`, `treino status-sync`, `iniciar-treino.bat`.
- Notificação do Windows quando chega treino novo.
- Migrações de banco com Alembic (o banco existente foi migrado sem perder dados).

### Alterado
- Duplicatas passam a considerar a fonte: o Strava prevalece sobre o Health Connect.

## [0.1.0] - 2026-10-27 (fase 1)

### Adicionado
- Importação do export do Strava (pasta ou .zip), com GPX, TCX e FIT.
- Parciais por km, zonas de FC, carga TRIMP, fitness, fadiga e forma.
- CLI `treino` e API com token.
